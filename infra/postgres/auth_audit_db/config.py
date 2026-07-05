from pydantic_settings import BaseSettings


class AuthAuditDbSettings(BaseSettings):
    model_config = {"env_prefix": "AUTH_AUDIT_"}

    database_url: str = "postgresql+asyncpg://st_user:st_pass@postgres:5432/scientific_tangle"

settings = AuthAuditDbSettings()