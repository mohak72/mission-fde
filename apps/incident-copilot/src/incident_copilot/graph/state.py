"""The diagnosis graph's state shape, threaded through every node.

A pydantic model, not a raw dict/TypedDict, per Coding Standards' rule that
anything crossing a module boundary uses pydantic.
[Source: architecture/coding-standards.md#language-specific-guidelines]
"""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from incident_copilot.graph.nodes.propose import DiagnosisResult
from incident_copilot.persistence.models import Alert, Runbook


class GraphState(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    alert: Alert
    alert_type: str | None = None
    runbook: Runbook | None = None
    diagnosis: DiagnosisResult | None = None
    grounded_in_live_state: bool = False
    approval_status: str | None = None


@dataclass
class PipelineContext:
    """Runtime-only dependencies (never persisted/replayed) injected into
    nodes via LangGraph's `context_schema`/`Runtime`, kept separate from
    `GraphState` -- a DB session is infrastructure, not pipeline data.
    """

    session: Session
