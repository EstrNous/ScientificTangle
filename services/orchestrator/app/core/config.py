from shared.config.settings import ServiceSettings


class Settings(ServiceSettings):
    service_name: str = "orchestrator"
    port: int = 8002
    auth_url: str = "http://auth_audit:8001"
    ingestion_url: str = "http://ingestion:8003"
    auth_jwt_issuer: str = "scientific-tangle-auth"
    auth_jwt_audience: str = "scientific-tangle-api"
    auth_jwks_cache_seconds: int = 300
    auth_clock_skew_seconds: int = 30


settings = Settings()
