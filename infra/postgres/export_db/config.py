from pydantic_settings import BaseSettings


class ExportDbSettings(BaseSettings):
    model_config = {"env_prefix": "EXPORT_"}

    database_url: str = "postgresql+asyncpg://st_user:st_pass@postgres:5432/export_db"

settings = ExportDbSettings()
