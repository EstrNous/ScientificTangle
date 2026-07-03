from shared.config.settings import ServiceSettings


class Settings(ServiceSettings):
    service_name: str = "retrieval"
    port: int = 8005


settings = Settings()
