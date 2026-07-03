from pydantic_settings import BaseSettings


class NotificationDbSettings(BaseSettings):
    model_config = {"env_prefix": "NOTIFICATION_"}

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/notification_db"
