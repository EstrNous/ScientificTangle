from pydantic_settings import BaseSettings


class OrchestratorDbSettings(BaseSettings):
    model_config = {"env_prefix": "ORCHESTRATOR_"}

    database_url: str = "postgresql+asyncpg://st_user:st_pass@postgres:5432/scientific_tangle"

settings = OrchestratorDbSettings()