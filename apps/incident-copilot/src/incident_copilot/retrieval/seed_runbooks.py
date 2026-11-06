"""Deterministic corpus seed script -- indexes the 10+ markdown runbooks under
`runbooks/` into Postgres + Chroma via `index_runbook()`.

Addition beyond the pinned Source Tree: closes the gap the architecture
checklist flagged ("No runbook corpus seed script named explicitly for
Story 1.3"). Idempotent -- safe to re-run (RunbookRepository.upsert is an
`ON CONFLICT DO UPDATE`, and Chroma's `upsert_embedding` overwrites by id).

Run as: `python -m incident_copilot.retrieval.seed_runbooks`
"""

from pathlib import Path

from sqlalchemy.orm import Session

from incident_copilot.persistence.models import Runbook, SessionLocal
from incident_copilot.retrieval.interface import index_runbook

RUNBOOKS_DIR = Path(__file__).resolve().parents[3] / "runbooks"

# Metadata lives here, not in the markdown files, to avoid adding a
# frontmatter-parsing dependency for something this small.
RUNBOOK_METADATA: list[dict] = [
    {
        "id": "pod-crashloop-oom",
        "title": "Pod CrashLoopBackOff: Out of Memory (OOMKilled)",
        "failure_mode_tags": ["crashloop", "oom", "memory"],
        "file": "pod-crashloop-oom.md",
    },
    {
        "id": "pod-crashloop-liveness-probe-failure",
        "title": "Pod CrashLoopBackOff: Failing Liveness Probe",
        "failure_mode_tags": ["crashloop", "liveness-probe"],
        "file": "pod-crashloop-liveness-probe-failure.md",
    },
    {
        "id": "image-pull-backoff",
        "title": "ImagePullBackOff / ErrImagePull",
        "failure_mode_tags": ["image-pull", "registry"],
        "file": "image-pull-backoff.md",
    },
    {
        "id": "pvc-pending-unbound",
        "title": "PersistentVolumeClaim Stuck Pending / Unbound",
        "failure_mode_tags": ["storage", "pvc"],
        "file": "pvc-pending-unbound.md",
    },
    {
        "id": "node-not-ready",
        "title": "Node NotReady",
        "failure_mode_tags": ["node", "kubelet"],
        "file": "node-not-ready.md",
    },
    {
        "id": "dns-resolution-failure",
        "title": "In-Cluster DNS Resolution Failure",
        "failure_mode_tags": ["dns", "coredns", "networking"],
        "file": "dns-resolution-failure.md",
    },
    {
        "id": "hpa-not-scaling",
        "title": "HorizontalPodAutoscaler Not Scaling",
        "failure_mode_tags": ["hpa", "autoscaling", "metrics"],
        "file": "hpa-not-scaling.md",
    },
    {
        "id": "certificate-expiry",
        "title": "TLS Certificate Expired (Ingress / cert-manager)",
        "failure_mode_tags": ["tls", "certificate", "cert-manager"],
        "file": "certificate-expiry.md",
    },
    {
        "id": "disk-pressure-eviction",
        "title": "Node Disk Pressure Causing Pod Eviction",
        "failure_mode_tags": ["disk-pressure", "eviction", "node"],
        "file": "disk-pressure-eviction.md",
    },
    {
        "id": "service-endpoint-mismatch",
        "title": "Service Has No Endpoints (Selector Mismatch)",
        "failure_mode_tags": ["service", "networking", "selector"],
        "file": "service-endpoint-mismatch.md",
    },
    {
        "id": "database-connection-pool-exhaustion",
        "title": "Database Connection Pool Exhaustion",
        "failure_mode_tags": ["database", "connection-pool"],
        "file": "database-connection-pool-exhaustion.md",
    },
]


def seed_runbooks(session: Session | None = None) -> int:
    """Indexes every runbook in RUNBOOK_METADATA. Returns the count indexed.

    Accepts an optional `session` so tests can seed against a dedicated test
    database instead of the dev `SessionLocal` -- defaults to the latter for
    the CLI entrypoint below.
    """
    owns_session = session is None
    session = session or SessionLocal()
    try:
        for entry in RUNBOOK_METADATA:
            content = (RUNBOOKS_DIR / entry["file"]).read_text()
            runbook = Runbook(
                id=entry["id"],
                title=entry["title"],
                content=content,
                failure_mode_tags=entry["failure_mode_tags"],
                team=None,
            )
            index_runbook(runbook, session)
        return len(RUNBOOK_METADATA)
    finally:
        if owns_session:
            session.close()


if __name__ == "__main__":
    count = seed_runbooks()
    print(f"Indexed {count} runbooks.")
