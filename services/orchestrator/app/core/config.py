from shared.config.settings import ServiceSettings


class Settings(ServiceSettings):
    service_name: str = "orchestrator"
    port: int = 8002


settings = Settings()
