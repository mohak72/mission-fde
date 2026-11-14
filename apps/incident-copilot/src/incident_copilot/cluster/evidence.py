"""The Cluster Evidence Tool (Story 2.3) -- strictly read-only `kubectl
get`/`describe`-equivalent calls against the target cluster.

This module may only call `get_*`/`list_*`/`read_*` on the Kubernetes API --
no `patch_*`/`delete_*`/`create_*`/`replace_*`, ever, here or anywhere else
against the target cluster. This is NFR5 enforced in code, not just in
review, and is independently checked by
`tests/unit/cluster/test_evidence_static_guard.py`.
[Source: architecture/components.md, architecture/coding-standards.md]
"""

import structlog
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from pydantic import BaseModel

from incident_copilot.persistence.models import Alert

logger = structlog.get_logger(component="cluster.evidence")

# No stated latency SLA exists for M1 (Test Strategy); this value is a
# deliberate fail-fast choice so AC4's degradation path triggers before a
# hung cluster call stalls the whole pipeline run, not a value derived from
# any requirement. [Source: docs/stories/2.3.read-only-kubectl-evidence-grounding.md]
_REQUEST_TIMEOUT_SECONDS = 10


class ClusterEvidenceError(Exception):
    """Raised on any Kubernetes API failure or timeout -- never caught in
    this module. `investigate.py` is where this is caught for graceful
    degradation (AC4), by design.
    [Source: docs/stories/2.3.read-only-kubectl-evidence-grounding.md]
    """


class ClusterEvidence(BaseModel):
    """No architecture doc defines this shape -- introduced here. `raw`
    carries anything `status_summary` doesn't capture, so a consumer never
    needs to re-query the cluster for detail already fetched once.
    """

    resource_kind: str
    resource_name: str
    namespace: str
    status_summary: str
    raw: dict


_cached_api_client: client.ApiClient | None = None


def _get_api_client() -> client.ApiClient:
    """Loads kubeconfig (local `kind` for dev/test, in-cluster config when
    deployed) once per process. Never reads the kubeconfig path/contents
    directly -- `kubernetes.config` handles that, so there is nothing here
    to accidentally log. [Source: architecture/coding-standards.md#critical-rules]
    """
    global _cached_api_client
    if _cached_api_client is None:
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        _cached_api_client = client.ApiClient()
    return _cached_api_client


def _resolve_target(alert: Alert) -> tuple[str, str, str] | None:
    """Resolves (kind, name, namespace) from the alert's labels. No doc
    specifies which labels identify the target resource -- recommended
    default: `namespace` + (`pod`, else `deployment`); if neither resource
    identifier is present, there is nothing to fetch (not a failure).
    [Source: docs/stories/2.3.read-only-kubectl-evidence-grounding.md]
    """
    labels: dict[str, str] = alert.payload.get("labels", {})
    namespace = labels.get("namespace")
    if not namespace:
        return None
    if pod := labels.get("pod"):
        return ("Pod", pod, namespace)
    if deployment := labels.get("deployment"):
        return ("Deployment", deployment, namespace)
    return None


def _describe_pod(core_v1: client.CoreV1Api, name: str, namespace: str) -> ClusterEvidence:
    pod = core_v1.read_namespaced_pod(
        name=name, namespace=namespace, _request_timeout=_REQUEST_TIMEOUT_SECONDS
    )
    events = core_v1.list_namespaced_event(
        namespace=namespace,
        field_selector=f"involvedObject.name={name}",
        _request_timeout=_REQUEST_TIMEOUT_SECONDS,
    )

    phase = pod.status.phase
    container_statuses = pod.status.container_statuses or []
    restart_count = sum(cs.restart_count for cs in container_statuses)
    waiting_reasons = [
        cs.state.waiting.reason
        for cs in container_statuses
        if cs.state and cs.state.waiting and cs.state.waiting.reason
    ]
    status_summary = f"pod {name} in phase {phase}, restart count {restart_count}"
    if waiting_reasons:
        status_summary = f"pod {name} in {waiting_reasons[0]}, restart count {restart_count}"

    return ClusterEvidence(
        resource_kind="Pod",
        resource_name=name,
        namespace=namespace,
        status_summary=status_summary,
        raw={
            "phase": phase,
            "restart_count": restart_count,
            "waiting_reasons": waiting_reasons,
            "recent_events": [e.reason for e in (events.items or [])][-5:],
        },
    )


def _describe_deployment(apps_v1: client.AppsV1Api, name: str, namespace: str) -> ClusterEvidence:
    deployment = apps_v1.read_namespaced_deployment(
        name=name, namespace=namespace, _request_timeout=_REQUEST_TIMEOUT_SECONDS
    )

    status = deployment.status
    available = status.available_replicas or 0
    desired = status.replicas or 0
    status_summary = f"deployment {name} has {available}/{desired} replicas available"

    return ClusterEvidence(
        resource_kind="Deployment",
        resource_name=name,
        namespace=namespace,
        status_summary=status_summary,
        raw={"available_replicas": available, "desired_replicas": desired},
    )


def get_evidence(alert: Alert) -> ClusterEvidence | None:
    """Returns live cluster evidence for the alert's target resource, or
    `None` if no resource is identifiable from the alert's labels (not a
    failure -- nothing to fetch). Raises `ClusterEvidenceError` on any
    Kubernetes API failure or timeout; does not catch it itself.
    [Source: architecture/components.md#cluster-evidence-tool]
    """
    target = _resolve_target(alert)
    if target is None:
        return None
    resource_kind, name, namespace = target

    try:
        api_client = _get_api_client()
        if resource_kind == "Pod":
            return _describe_pod(client.CoreV1Api(api_client), name, namespace)
        return _describe_deployment(client.AppsV1Api(api_client), name, namespace)
    except ApiException as exc:
        raise ClusterEvidenceError(
            f"Kubernetes API call failed for {resource_kind} {namespace}/{name}: {exc}"
        ) from exc
    except TimeoutError as exc:
        raise ClusterEvidenceError(
            f"Kubernetes API call timed out for {resource_kind} {namespace}/{name}"
        ) from exc
