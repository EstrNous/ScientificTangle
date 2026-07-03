from pydantic_settings import BaseSettings


class AuthAuditDbSettings(BaseSettings):
    model_config = {"env_prefix": "AUTH_AUDIT_"}

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/orchestrator_db"

settings = AuthAuditDbSettings()