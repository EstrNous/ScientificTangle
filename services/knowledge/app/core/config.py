from shared.config.settings import ServiceSettings


class Settings(ServiceSettings):
    service_name: str = "knowledge"
    port: int = 8004


settings = Settings()
