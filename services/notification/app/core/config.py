from pydantic_settings import SettingsConfigDict

from shared.config.settings import ServiceSettings


class Settings(ServiceSettings):
    service_name: str = "notification"
    port: int = 8008
    auth_url: str = "http://auth_audit:8001"
    model_url: str = "http://model:8006"
    auth_jwt_issuer: str = "scientific-tangle-auth"
    auth_jwt_audience: str = "scientific-tangle-api"
    auth_jwks_cache_seconds: int = 300
    auth_clock_skew_seconds: int = 30
    notification_list_limit: int = 20
    match_score_threshold: float = 0.4
    notification_redis_pubsub_enabled: bool = True
    notification_redis_delivery_channel: str = "scientific_tangle:notifications:delivery"
    notification_redis_created_channel: str = "scientific_tangle:notifications:created"
    notification_redis_retry_seconds: int = 5
    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")


settings = Settings()
