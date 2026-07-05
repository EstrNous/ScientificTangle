from pydantic_settings import SettingsConfigDict

from shared.config.settings import ServiceSettings


class Settings(ServiceSettings):
    service_name: str = "retrieval"
    port: int = 8005
    model_url: str = "http://model:8006"
    knowledge_url: str = "http://knowledge:8004"
    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")


settings = Settings()
