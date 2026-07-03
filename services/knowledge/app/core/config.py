from shared.config.settings import ServiceSettings
from pydantic_settings import SettingsConfigDict


class Settings(ServiceSettings):
    service_name: str = "knowledge"
    port: int = 8004
    model_url: str = "http://model:8006"
    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")


settings = Settings()
