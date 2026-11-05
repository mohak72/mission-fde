from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed, env-based config. Per Coding Standards: this is the ONLY module
    that reads raw environment variables (NFR7) — everything else imports
    a Settings instance.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "incident-copilot"
    environment: str = "local"
    database_url: str = "postgresql+psycopg://incident_copilot:incident_copilot@localhost:5432/incident_copilot"
    webhook_hmac_secret: str = "dev-only-insecure-secret-change-me"  # noqa: S105 -- placeholder, overridden via .env


settings = Settings()
