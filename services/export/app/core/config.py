from shared.config.settings import ServiceSettings


class Settings(ServiceSettings):
    service_name: str = "export"
    port: int = 8007


settings = Settings()
