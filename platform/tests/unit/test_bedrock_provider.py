from platform_core.gateway import bedrock_provider


def test_converse_extracts_text_from_well_formed_response(mocker) -> None:
    mock_client = mocker.Mock()
    mock_client.converse.return_value = {
        "output": {"message": {"content": [{"text": "probable cause: OOM"}]}}
    }
    mocker.patch("platform_core.gateway.bedrock_provider._get_client", return_value=mock_client)

    text = bedrock_provider.converse("diagnose this alert", model_id="m", timeout_seconds=30)

    assert text == "probable cause: OOM"


def test_converse_raises_key_error_on_malformed_response_shape(mocker) -> None:
    """REL-001: a malformed/unexpected Bedrock response shape (e.g. an empty
    content list) must surface as a raw KeyError/IndexError here -- this
    module's contract is "raise whatever the SDK/shape gives us"; translating
    that to GatewayError is gateway.py's job (see its own except clause)."""
    mock_client = mocker.Mock()
    mock_client.converse.return_value = {"output": {"message": {"content": []}}}
    mocker.patch("platform_core.gateway.bedrock_provider._get_client", return_value=mock_client)

    try:
        bedrock_provider.converse("diagnose this alert", model_id="m", timeout_seconds=30)
    except IndexError:
        pass
    else:
        raise AssertionError("expected IndexError for an empty content list")
