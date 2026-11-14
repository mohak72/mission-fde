"""AC1/AC3/AC4: the investigate node against a real local `kind` cluster --
mocking Kubernetes here would test nothing meaningful (Test Strategy).
LLM Gateway stays mocked, same asymmetric-mocking convention as every other
integration test in this tier.
[Source: architecture/test-strategy-and-standards.md#integration-tests]

NOTE: this file requires a real local `kind` cluster with a kubeconfig
pointing at it (set up by `helm/kind-action` in CI). It could not be
executed in the sandbox that implemented this story -- no `kind`/`kubectl`
binary is available there and installing one was blocked by sandbox policy.
See this story's Dev Agent Record / Debug Log References.
"""

import time
import uuid

import pytest
from kubernetes import client, config
from sqlalchemy.orm import Session

from incident_copilot.graph.pipeline import run_pipeline
from incident_copilot.persistence.models import DiagnosisProposal
from incident_copilot.persistence.repositories import AlertRepository
from incident_copilot.retrieval.seed_runbooks import seed_runbooks

MOCK_LLM_RESPONSE = (
    "Cause: Container exceeded its memory limit\n"
    "Action: Raise resources.limits.memory\n"
    "Citation: Resolution"
)


def _k8s_available() -> bool:
    try:
        config.load_kube_config()
    except config.ConfigException:
        return False
    return True


pytestmark = pytest.mark.skipif(
    not _k8s_available(), reason="no local kind cluster / kubeconfig available"
)


@pytest.fixture
def crashing_pod():
    """Creates a namespace + a deliberately-crashing pod via the Kubernetes
    client (never a shell `kubectl apply`, per tech-stack.md's rationale for
    choosing the client library), waits for at least one restart, then
    tears both down.
    """
    core_v1 = client.CoreV1Api()
    namespace = f"story-2-3-test-{uuid.uuid4().hex[:8]}"
    pod_name = "crashing-pod"

    core_v1.create_namespace(client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace)))
    core_v1.create_namespaced_pod(
        namespace=namespace,
        body=client.V1Pod(
            metadata=client.V1ObjectMeta(name=pod_name),
            spec=client.V1PodSpec(
                containers=[
                    client.V1Container(
                        name="crasher",
                        image="busybox",
                        command=["sh", "-c", "exit 1"],
                    )
                ],
                restart_policy="Always",
            ),
        ),
    )

    deadline = time.monotonic() + 60
    restart_count = 0
    while time.monotonic() < deadline:
        pod = core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        statuses = pod.status.container_statuses or []
        restart_count = sum(cs.restart_count for cs in statuses)
        if restart_count >= 1:
            break
        time.sleep(2)

    assert restart_count >= 1, "fixture pod never restarted -- can't exercise a real crash loop"

    yield namespace, pod_name

    core_v1.delete_namespace(namespace)


def test_investigate_grounds_diagnosis_in_real_cluster_evidence(
    mocker, db_session: Session, crashing_pod
) -> None:
    namespace, pod_name = crashing_pod
    alert, _ = AlertRepository(db_session).insert_if_new(
        "k8s-evidence-1",
        {
            "labels": {
                "alertname": "KubePodCrashLooping",
                "namespace": namespace,
                "pod": pod_name,
            },
            "annotations": {},
        },
        signature_verified=True,
    )
    seed_runbooks(db_session)
    mocker.patch(
        "incident_copilot.graph.nodes.propose.complete",
        return_value=mocker.Mock(content=MOCK_LLM_RESPONSE),
    )

    run = run_pipeline(alert, db_session)

    assert run.status == "completed"
    proposal = (
        db_session.query(DiagnosisProposal)
        .filter(DiagnosisProposal.pipeline_run_id == run.id)
        .one()
    )
    assert proposal.grounded_in_live_state is True
    assert proposal.live_evidence is not None
    assert proposal.live_evidence["resource_name"] == pod_name


def test_investigate_degrades_gracefully_when_resource_does_not_exist(
    mocker, db_session: Session
) -> None:
    alert, _ = AlertRepository(db_session).insert_if_new(
        "k8s-evidence-2",
        {
            "labels": {
                "alertname": "KubePodCrashLooping",
                "namespace": "nonexistent-namespace",
                "pod": "nonexistent-pod",
            },
            "annotations": {},
        },
        signature_verified=True,
    )
    seed_runbooks(db_session)
    mocker.patch(
        "incident_copilot.graph.nodes.propose.complete",
        return_value=mocker.Mock(content=MOCK_LLM_RESPONSE),
    )

    run = run_pipeline(alert, db_session)

    assert run.status == "completed"
    proposal = (
        db_session.query(DiagnosisProposal)
        .filter(DiagnosisProposal.pipeline_run_id == run.id)
        .one()
    )
    assert proposal.grounded_in_live_state is False
    assert proposal.live_evidence is None
