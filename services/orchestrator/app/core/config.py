from shared.config.settings import ServiceSettings
from pydantic_settings import SettingsConfigDict


class Settings(ServiceSettings):
    service_name: str = "orchestrator"
    port: int = 8002
    auth_url: str = "http://auth_audit:8001"
    ingestion_url: str = "http://ingestion:8003"
    retrieval_url: str = "http://retrieval:8005"
    model_url: str = "http://model:8006"
    auth_jwt_issuer: str = "scientific-tangle-auth"
    auth_jwt_audience: str = "scientific-tangle-api"
    auth_jwks_cache_seconds: int = 300
    auth_clock_skew_seconds: int = 30
    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")


settings = Settings()
