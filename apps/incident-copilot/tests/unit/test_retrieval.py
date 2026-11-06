from incident_copilot.persistence.models import Alert, Runbook
from incident_copilot.retrieval import interface


def test_index_runbook_persists_metadata_and_embeds_content(mocker) -> None:
    mock_repo_cls = mocker.patch("incident_copilot.retrieval.interface.RunbookRepository")
    mock_upsert_embedding = mocker.patch("incident_copilot.retrieval.interface.upsert_embedding")
    runbook = Runbook(
        id="pod-crashloop-oom",
        title="Pod CrashLoopBackOff: OOM",
        content="...",
        failure_mode_tags=["oom"],
        team=None,
    )
    session = object()

    interface.index_runbook(runbook, session)

    mock_repo_cls.assert_called_once_with(session)
    mock_repo_cls.return_value.upsert.assert_called_once_with(
        runbook_id="pod-crashloop-oom",
        title="Pod CrashLoopBackOff: OOM",
        content="...",
        failure_mode_tags=["oom"],
        team=None,
    )
    mock_upsert_embedding.assert_called_once_with("pod-crashloop-oom", "...")


def test_retrieve_runbook_returns_nearest_match(mocker) -> None:
    mocker.patch(
        "incident_copilot.retrieval.interface.query_nearest", return_value=["node-not-ready"]
    )
    expected_runbook = Runbook(
        id="node-not-ready", title="Node NotReady", content="...", failure_mode_tags=[], team=None
    )
    mock_repo_cls = mocker.patch("incident_copilot.retrieval.interface.RunbookRepository")
    mock_repo_cls.return_value.get_by_id.return_value = expected_runbook
    alert = Alert(
        id=None,
        external_alert_id="a1",
        payload={"labels": {"alertname": "KubeNodeNotReady"}, "annotations": {}},
        received_at=None,
        signature_verified=True,
    )
    session = object()

    result = interface.retrieve_runbook(alert, session)

    assert result is expected_runbook
    mock_repo_cls.return_value.get_by_id.assert_called_once_with("node-not-ready")


def test_retrieve_runbook_returns_none_when_chroma_has_no_match(mocker) -> None:
    mocker.patch("incident_copilot.retrieval.interface.query_nearest", return_value=[])
    mocker.patch("incident_copilot.retrieval.interface.RunbookRepository")
    alert = Alert(
        id=None,
        external_alert_id="a1",
        payload={"labels": {}, "annotations": {}},
        received_at=None,
        signature_verified=True,
    )

    result = interface.retrieve_runbook(alert, object())

    assert result is None


def test_retrieve_runbook_logs_latency_and_embedding_model(mocker) -> None:
    mocker.patch("incident_copilot.retrieval.interface.query_nearest", return_value=["x"])
    mocker.patch("incident_copilot.retrieval.interface.RunbookRepository")
    mock_logger = mocker.patch("incident_copilot.retrieval.interface.logger")
    alert = Alert(
        id=None,
        external_alert_id="a1",
        payload={"labels": {}, "annotations": {}},
        received_at=None,
        signature_verified=True,
    )

    interface.retrieve_runbook(alert, object())

    mock_logger.info.assert_called_once()
    _, kwargs = mock_logger.info.call_args
    assert "latency_ms" in kwargs
    assert kwargs["embedding_model"] == interface.EMBEDDING_MODEL_NAME


def test_query_text_for_alert_concatenates_labels_and_annotations() -> None:
    alert = Alert(
        id=None,
        external_alert_id="a1",
        payload={
            "labels": {"alertname": "KubePodCrashLooping"},
            "annotations": {"summary": "Pod is crash looping"},
        },
        received_at=None,
        signature_verified=True,
    )

    query_text = interface._query_text_for_alert(alert)

    assert "KubePodCrashLooping" in query_text
    assert "Pod is crash looping" in query_text
