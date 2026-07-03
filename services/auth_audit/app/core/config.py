from shared.config.settings import ServiceSettings


class Settings(ServiceSettings):
    service_name: str = "auth-audit"
    port: int = 8001


settings = Settings()
