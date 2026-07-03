from pydantic_settings import BaseSettings


class OrchestratorDbSettings(BaseSettings):
    model_config = {"env_prefix": "ORCHESTRATOR_"}

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/orchestrator_db"

settings = OrchestratorDbSettings()