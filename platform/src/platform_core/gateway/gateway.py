"""The LLM Gateway: the single seam (NFR1) between any component and any
model provider. [Source: architecture/components.md#llm-gateway-platform]

Retry + timeout only in this story -- the circuit breaker is deliberately
deferred (it protects a rate-limit budget that doesn't exist until Story
3.2's token-bucket limiter is built; see Story 2.1 Completion Notes).
"""

import random
import time

from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from platform_core.config import settings
from platform_core.gateway.bedrock_provider import converse

MAX_ATTEMPTS = 3
TIMEOUT_SECONDS = 30

# Bedrock error codes considered transient -- everything else (validation,
# access-denied, not-found) indicates a bug, not a blip, and is never retried.
_TRANSIENT_ERROR_CODES = {
    "ThrottlingException",
    "ServiceUnavailableException",
    "InternalServerException",
    "ModelTimeoutException",
}


class GatewayError(Exception):
    """Raised for any LLM provider failure. Nothing outside this module may
    catch a raw `botocore` exception -- this is what every caller sees
    instead. [Source: architecture/coding-standards.md#critical-rules]
    """


class LLMResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class ModelConfig:
    def __init__(self, model_id: str | None = None) -> None:
        self.model_id = model_id or settings.bedrock_model_id


def _is_transient(exc: Exception) -> bool:
    if isinstance(exc, NoCredentialsError):
        return False  # missing config, not a blip -- retrying won't help
    if isinstance(exc, ClientError):
        code = exc.response.get("Error", {}).get("Code", "")
        return code in _TRANSIENT_ERROR_CODES
    return isinstance(exc, BotoCoreError)  # connection/endpoint-level issues


def complete(prompt: str, model_config: ModelConfig | None = None) -> LLMResponse:
    """The only method any other component may call to reach a model.

    Exponential backoff with jitter, max 3 attempts, transient errors only.
    [Source: architecture/error-handling-strategy.md#external-api-errors]
    """
    model_config = model_config or ModelConfig()
    last_error: Exception | None = None

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            text = converse(prompt, model_id=model_config.model_id, timeout_seconds=TIMEOUT_SECONDS)
            return LLMResponse(content=text)
        except (ClientError, BotoCoreError) as exc:
            last_error = exc
            if not _is_transient(exc) or attempt == MAX_ATTEMPTS:
                raise GatewayError(f"Bedrock call failed: {exc}") from exc
            # retry jitter, not crypto
            time.sleep((2 ** (attempt - 1)) + random.uniform(0, 1))  # noqa: S311 # nosec B311

    raise GatewayError(f"Bedrock call failed: {last_error}") from last_error
