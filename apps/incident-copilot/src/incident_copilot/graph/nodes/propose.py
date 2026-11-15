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
{live_evidence_section}"""

_LIVE_EVIDENCE_TEMPLATE = """
Live Cluster Evidence (from a real-time read-only kubectl check):
{status_summary}

Incorporate this live evidence into the Cause line above -- it reflects what is \
actually happening right now, not just the generic runbook scenario.
"""


class DiagnosisResult(BaseModel):
    matched: bool
    cause: str | None = None
    next_step_action: str | None = None
    runbook_citation: str | None = None


def _build_prompt(alert: Alert, runbook: Runbook, live_evidence: dict | None) -> str:
    labels: dict[str, str] = alert.payload.get("labels", {})
    annotations: dict[str, str] = alert.payload.get("annotations", {})
    alert_summary = ", ".join(f"{k}={v}" for k, v in {**labels, **annotations}.items())
    live_evidence_section = ""
    if live_evidence is not None:
        live_evidence_section = _LIVE_EVIDENCE_TEMPLATE.format(
            status_summary=live_evidence["status_summary"]
        )
    return _PROMPT_TEMPLATE.format(
        alert_summary=alert_summary,
        runbook_title=runbook.title,
        runbook_content=runbook.content,
        live_evidence_section=live_evidence_section,
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


def propose_diagnosis(
    alert: Alert, session: Session, live_evidence: dict | None = None
) -> DiagnosisResult:
    """AC1/AC2: calls the Gateway and returns a structured cause/action/
    citation. AC3: if `retrieve_runbook` found nothing above the confidence
    threshold, returns `matched=False` **without ever calling the Gateway**
    -- this is the actual hallucination guard, not just a label on the
    output. [Source: architecture/components.md#diagnosis-graph]

    `live_evidence` (Story 2.3): when provided, folded into the prompt so
    the Cause line itself cites it (AC3). Omitting it (the default)
    produces a byte-identical prompt to Story 2.1/2.2's behavior.
    """
    runbook = retrieve_runbook(alert, session)
    if runbook is None:
        return DiagnosisResult(matched=False)

    prompt = _build_prompt(alert, runbook, live_evidence)
    response = complete(prompt)
    return _parse_response(response.content)
