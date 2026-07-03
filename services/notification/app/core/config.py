from shared.config.settings import ServiceSettings


class Settings(ServiceSettings):
    service_name: str = "notification"
    port: int = 8008


settings = Settings()
