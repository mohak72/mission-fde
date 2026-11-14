from kubernetes.client.exceptions import ApiException

from incident_copilot.cluster.evidence import ClusterEvidenceError, get_evidence
from incident_copilot.persistence.models import Alert


def _alert(labels: dict[str, str]) -> Alert:
    return Alert(
        id=None,
        external_alert_id="a1",
        payload={"labels": labels, "annotations": {}},
        received_at=None,
        signature_verified=True,
    )


def test_get_evidence_returns_none_when_no_resource_identifiable(mocker) -> None:
    get_client = mocker.patch("incident_copilot.cluster.evidence._get_api_client")

    result = get_evidence(_alert({}))

    assert result is None
    get_client.assert_not_called()


def test_get_evidence_returns_none_when_namespace_missing_even_with_pod(mocker) -> None:
    get_client = mocker.patch("incident_copilot.cluster.evidence._get_api_client")

    result = get_evidence(_alert({"pod": "api-7f8"}))

    assert result is None
    get_client.assert_not_called()


def test_get_evidence_describes_pod_from_pod_label(mocker) -> None:
    mocker.patch("incident_copilot.cluster.evidence._get_api_client")
    mock_core_v1 = mocker.Mock()
    mocker.patch("incident_copilot.cluster.evidence.client.CoreV1Api", return_value=mock_core_v1)

    container_status = mocker.Mock(restart_count=7)
    container_status.state.waiting.reason = "CrashLoopBackOff"
    mock_core_v1.read_namespaced_pod.return_value = mocker.Mock(
        status=mocker.Mock(phase="Running", container_statuses=[container_status])
    )
    mock_core_v1.list_namespaced_event.return_value = mocker.Mock(
        items=[mocker.Mock(reason="BackOff")]
    )

    evidence = get_evidence(_alert({"namespace": "prod", "pod": "api-7f8"}))

    assert evidence is not None
    assert evidence.resource_kind == "Pod"
    assert evidence.resource_name == "api-7f8"
    assert evidence.namespace == "prod"
    assert "CrashLoopBackOff" in evidence.status_summary
    assert "7" in evidence.status_summary
    assert evidence.raw["restart_count"] == 7
    mock_core_v1.read_namespaced_pod.assert_called_once_with(
        name="api-7f8", namespace="prod", _request_timeout=10
    )


def test_get_evidence_describes_deployment_fallback_when_no_pod_label(mocker) -> None:
    mocker.patch("incident_copilot.cluster.evidence._get_api_client")
    mock_apps_v1 = mocker.Mock()
    mocker.patch("incident_copilot.cluster.evidence.client.AppsV1Api", return_value=mock_apps_v1)
    mock_apps_v1.read_namespaced_deployment.return_value = mocker.Mock(
        status=mocker.Mock(available_replicas=2, replicas=3)
    )

    evidence = get_evidence(_alert({"namespace": "prod", "deployment": "api"}))

    assert evidence is not None
    assert evidence.resource_kind == "Deployment"
    assert evidence.resource_name == "api"
    assert "2/3" in evidence.status_summary


def test_get_evidence_raises_cluster_evidence_error_on_api_exception(mocker) -> None:
    mocker.patch("incident_copilot.cluster.evidence._get_api_client")
    mock_core_v1 = mocker.Mock()
    mocker.patch("incident_copilot.cluster.evidence.client.CoreV1Api", return_value=mock_core_v1)
    mock_core_v1.read_namespaced_pod.side_effect = ApiException(status=500, reason="boom")

    try:
        get_evidence(_alert({"namespace": "prod", "pod": "api-7f8"}))
    except ClusterEvidenceError:
        pass
    else:
        raise AssertionError("expected ClusterEvidenceError")


def test_get_evidence_raises_cluster_evidence_error_on_timeout(mocker) -> None:
    mocker.patch("incident_copilot.cluster.evidence._get_api_client")
    mock_core_v1 = mocker.Mock()
    mocker.patch("incident_copilot.cluster.evidence.client.CoreV1Api", return_value=mock_core_v1)
    mock_core_v1.read_namespaced_pod.side_effect = TimeoutError("timed out")

    try:
        get_evidence(_alert({"namespace": "prod", "pod": "api-7f8"}))
    except ClusterEvidenceError:
        pass
    else:
        raise AssertionError("expected ClusterEvidenceError")
