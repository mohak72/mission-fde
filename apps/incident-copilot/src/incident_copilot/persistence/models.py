import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from incident_copilot.config import settings


class Base(DeclarativeBase):
    pass


class Alert(Base):
    """Matches the `alerts` table. [Source: architecture/database-schema.md]"""

    __tablename__ = "alerts"
    __table_args__ = (
        Index("idx_alerts_dedup_group", "dedup_group_id"),
        Index("idx_alerts_received_at", "received_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    external_alert_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    payload: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    signature_verified: Mapped[bool] = mapped_column(Boolean, nullable=False)
    team: Mapped[str | None] = mapped_column(String, nullable=True)
    dedup_group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)


class Runbook(Base):
    """Matches the `runbooks` table. [Source: architecture/database-schema.md]

    The vector embedding of `content` is not a field here -- it's a Chroma
    index entry addressed by this model's `id`.
    """

    __tablename__ = "runbooks"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    content: Mapped[str] = mapped_column(String, nullable=False)
    failure_mode_tags: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, default=list, server_default="{}"
    )
    team: Mapped[str | None] = mapped_column(String, nullable=True)


class PipelineRun(Base):
    """Matches the `pipeline_runs` table. [Source: architecture/database-schema.md]"""

    __tablename__ = "pipeline_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'failed')", name="ck_pipeline_runs_status"
        ),
        Index("idx_pipeline_runs_alert", "alert_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("alerts.id"), nullable=False
    )
    status: Mapped[str] = mapped_column(String, nullable=False, default="running")
    node_transitions: Mapped[list] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list, server_default="[]"
    )
    llm_provider_config: Mapped[str] = mapped_column(String, nullable=False)


class DiagnosisProposal(Base):
    """Matches the `diagnosis_proposals` table. [Source: architecture/database-schema.md]"""

    __tablename__ = "diagnosis_proposals"
    __table_args__ = (
        Index("idx_proposals_run", "pipeline_run_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pipeline_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("pipeline_runs.id"), nullable=False
    )
    runbook_id: Mapped[str | None] = mapped_column(String, ForeignKey("runbooks.id"), nullable=True)
    cause: Mapped[str] = mapped_column(String, nullable=False)
    next_step_action: Mapped[str] = mapped_column(String, nullable=False)
    runbook_citation: Mapped[str | None] = mapped_column(String, nullable=True)
    live_evidence: Mapped[dict | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    grounded_in_live_state: Mapped[bool] = mapped_column(Boolean, nullable=False)


def make_engine(database_url: str | None = None) -> Engine:
    from sqlalchemy import create_engine

    return create_engine(database_url or settings.database_url)


engine: Engine = make_engine()
SessionLocal: sessionmaker[Session] = sessionmaker(bind=engine, expire_on_commit=False)
