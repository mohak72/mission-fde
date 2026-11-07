from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, env-based config. Per Coding Standards: this is the ONLY module
    that reads raw environment variables (NFR7) — everything else imports a
    Settings instance.

    AWS credentials themselves are not modeled here -- boto3 reads those via
    its own standard credential chain (env vars / shared config / IAM role),
    which is AWS's own convention, not a secret this app manages directly.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    aws_region: str = "us-east-1"
    # Amazon Nova Micro: cheapest/fastest Bedrock model, suitable for a
    # structured triage task rather than open-ended reasoning -- see Story
    # 2.1 Completion Notes for the full rationale.
    bedrock_model_id: str = "amazon.nova-micro-v1:0"


settings = Settings()
