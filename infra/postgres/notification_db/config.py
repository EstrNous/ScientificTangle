from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class NotificationDbSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="NOTIFICATION_",
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    database_url: str = Field(
        default="postgresql+asyncpg://st_user:st_pass@postgres:5432/scientific_tangle",
        validation_alias=AliasChoices("NOTIFICATION_DATABASE_URL", "POSTGRES_URL"),
    )


settings = NotificationDbSettings()