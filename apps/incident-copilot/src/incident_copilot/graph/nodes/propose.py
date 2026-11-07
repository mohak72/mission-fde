"""The "propose" node's core logic -- placed here ahead of Story 2.2's
LangGraph refactor, which will wrap this into an actual graph node rather
than needing to migrate it out of some other temporary location.
[Source: architecture/source-tree.md, docs/stories/2.1.llm-triage-summary.md]
"""

from platform_core.gateway.gateway import GatewayError, complete
from pydantic import BaseModel
from sqlalchemy.orm import Session

from incident_copilot.persistence.models import Alert, Runbook
from incident_copilot.retrieval.interface import retrieve_runbook

_PROMPT_TEMPLATE = """You are an on-call diagnosis assistant. An alert has fired and a \
matching runbook has been found. Using ONLY the runbook content below, answer in \
exactly this format, three lines, no extra commentary:

Cause: <probable cause, one sentence>
Action: <the single next-step action to take, one sentence>
Citation: <the specific runbook section/heading you drew this from>

Alert:
{alert_summary}

Runbook ({runbook_title}):
{runbook_content}
"""


class DiagnosisResult(BaseModel):
    matched: bool
    cause: str | None = None
    next_step_action: str | None = None
    runbook_citation: str | None = None


def _build_prompt(alert: Alert, runbook: Runbook) -> str:
    labels: dict[str, str] = alert.payload.get("labels", {})
    annotations: dict[str, str] = alert.payload.get("annotations", {})
    alert_summary = ", ".join(f"{k}={v}" for k, v in {**labels, **annotations}.items())
    return _PROMPT_TEMPLATE.format(
        alert_summary=alert_summary,
        runbook_title=runbook.title,
        runbook_content=runbook.content,
    )


def _parse_response(text: str) -> DiagnosisResult:
    """Raises `GatewayError` if the LLM didn't follow the required 3-line
    format -- returning `matched=True` with missing fields would silently
    violate AC2 (explicit citation) in a way callers can't detect.
    [QA Story 2.1 REL-002]
    """
    fields: dict[str, str | None] = {"cause": None, "action": None, "citation": None}
    prefixes = (("cause", "Cause:"), ("action", "Action:"), ("citation", "Citation:"))
    for line in text.splitlines():
        stripped = line.strip()
        for key, prefix in prefixes:
            if stripped.startswith(prefix):
                fields[key] = stripped[len(prefix) :].strip()
    if any(value is None for value in fields.values()):
        raise GatewayError(
            f"LLM response did not match the expected Cause/Action/Citation format: {text!r}"
        )
    return DiagnosisResult(
        matched=True,
        cause=fields["cause"],
        next_step_action=fields["action"],
        runbook_citation=fields["citation"],
    )


def propose_diagnosis(alert: Alert, session: Session) -> DiagnosisResult:
    """AC1/AC2: calls the Gateway and returns a structured cause/action/
    citation. AC3: if `retrieve_runbook` found nothing above the confidence
    threshold, returns `matched=False` **without ever calling the Gateway**
    -- this is the actual hallucination guard, not just a label on the
    output. [Source: architecture/components.md#diagnosis-graph]
    """
    runbook = retrieve_runbook(alert, session)
    if runbook is None:
        return DiagnosisResult(matched=False)

    prompt = _build_prompt(alert, runbook)
    response = complete(prompt)
    return _parse_response(response.content)
