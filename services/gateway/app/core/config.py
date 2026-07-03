from shared.config.settings import ServiceSettings
from pydantic_settings import SettingsConfigDict


class Settings(ServiceSettings):
    service_name: str = "gateway"
    port: int = 8000
    auth_url: str = "http://auth_audit:8001"
    orchestrator_url: str = "http://orchestrator:8002"
    auth_jwt_issuer: str = "scientific-tangle-auth"
    auth_jwt_audience: str = "scientific-tangle-api"
    auth_jwks_cache_seconds: int = 300
    auth_clock_skew_seconds: int = 30
    upload_limit_bytes: int = 100 * 1024 * 1024
    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")
