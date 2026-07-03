from shared.config.settings import ServiceSettings


class Settings(ServiceSettings):
    service_name: str = "ingestion"
    port: int = 8003


settings = Settings()
