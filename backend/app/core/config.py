from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://drift:drift_secret@localhost:5432/drift_sentinel"
    database_url_sync: str = "postgresql://drift:drift_secret@localhost:5432/drift_sentinel"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # MLflow
    mlflow_tracking_uri: str = "http://localhost:5001"

    # Auth
    secret_key: str = "dev-secret-key"
    access_token_expire_minutes: int = 60

    # App
    app_env: str = "development"
    log_level: str = "INFO"


settings = Settings()
