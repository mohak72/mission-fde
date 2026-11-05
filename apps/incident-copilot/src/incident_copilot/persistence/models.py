import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
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


def make_engine(database_url: str | None = None) -> Engine:
    from sqlalchemy import create_engine

    return create_engine(database_url or settings.database_url)


engine: Engine = make_engine()
SessionLocal: sessionmaker[Session] = sessionmaker(bind=engine, expire_on_commit=False)
