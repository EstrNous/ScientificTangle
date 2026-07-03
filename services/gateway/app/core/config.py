from shared.config.settings import ServiceSettings


class Settings(ServiceSettings):
    service_name: str = "gateway"
    port: int = 8000


settings = Settings()
