from pydantic_settings import BaseSettings


class ExportDbSettings(BaseSettings):
    model_config = {"env_prefix": "EXPORT_"}

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/export_db"

settings = ExportDbSettings()