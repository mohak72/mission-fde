import pytest
from botocore.exceptions import ClientError

from platform_core.gateway.gateway import GatewayError, complete


def _client_error(code: str) -> ClientError:
    return ClientError(error_response={"Error": {"Code": code}}, operation_name="Converse")


def test_complete_happy_path(mocker) -> None:
    mocker.patch("platform_core.gateway.gateway.converse", return_value="probable cause: OOM")

    response = complete("diagnose this alert")

    assert response.content == "probable cause: OOM"


def test_complete_retries_transient_error_then_succeeds(mocker) -> None:
    mocker.patch("platform_core.gateway.gateway.time.sleep")
    mock_converse = mocker.patch(
        "platform_core.gateway.gateway.converse",
        side_effect=[_client_error("ThrottlingException"), "recovered"],
    )

    response = complete("diagnose this alert")

    assert response.content == "recovered"
    assert mock_converse.call_count == 2


def test_complete_raises_gateway_error_after_exhausting_retries(mocker) -> None:
    mocker.patch("platform_core.gateway.gateway.time.sleep")
    mock_converse = mocker.patch(
        "platform_core.gateway.gateway.converse",
        side_effect=_client_error("ThrottlingException"),
    )

    with pytest.raises(GatewayError):
        complete("diagnose this alert")

    assert mock_converse.call_count == 3


def test_complete_does_not_retry_non_transient_error(mocker) -> None:
    mocker.patch("platform_core.gateway.gateway.time.sleep")
    mock_converse = mocker.patch(
        "platform_core.gateway.gateway.converse",
        side_effect=_client_error("ValidationException"),
    )

    with pytest.raises(GatewayError):
        complete("diagnose this alert")

    assert mock_converse.call_count == 1


def test_complete_raises_gateway_error_on_malformed_response_shape(mocker) -> None:
    """REL-001: an unexpected Bedrock response shape (surfacing as a raw
    KeyError/IndexError from `converse`) must be translated to GatewayError,
    never retried, and never leak past the Gateway seam."""
    mocker.patch("platform_core.gateway.gateway.time.sleep")
    mock_converse = mocker.patch(
        "platform_core.gateway.gateway.converse",
        side_effect=KeyError("output"),
    )

    with pytest.raises(GatewayError):
        complete("diagnose this alert")

    assert mock_converse.call_count == 1
