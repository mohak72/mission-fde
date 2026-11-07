"""The only module in this project permitted to import boto3.

[Source: architecture/coding-standards.md#critical-rules]
"""

import boto3
from botocore.config import Config

from platform_core.config import settings

_client = None


def _get_client(timeout_seconds: int):
    global _client
    if _client is None:
        _client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            config=Config(connect_timeout=timeout_seconds, read_timeout=timeout_seconds),
        )
    return _client


def converse(prompt: str, model_id: str, timeout_seconds: int) -> str:
    """Calls Bedrock's Converse API with a single user message, returns the
    model's text response.

    Raises whatever `botocore.exceptions.ClientError`/`BotoCoreError` the SDK
    raises -- translating those to `GatewayError` is `gateway.py`'s job, not
    this module's (this module's only responsibility is the raw API call).
    """
    client = _get_client(timeout_seconds)
    response = client.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": prompt}]}],
    )
    return response["output"]["message"]["content"][0]["text"]
