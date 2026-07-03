from shared.config.settings import ServiceSettings


class Settings(ServiceSettings):
    service_name: str = "model"
    port: int = 8006


settings = Settings()
