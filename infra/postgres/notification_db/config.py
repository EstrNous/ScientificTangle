from pydantic_settings import BaseSettings


class NotificationDbSettings(BaseSettings):
    model_config = {"env_prefix": "GATEWAY_"}

    database_url: str = "postgresql+asyncpg://st_user:st_pass@postgres:5432/scientific_tangle"


settings = NotificationDbSettings()