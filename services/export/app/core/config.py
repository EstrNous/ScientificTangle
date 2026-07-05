from pydantic_settings import SettingsConfigDict

from shared.config.settings import ServiceSettings


class Settings(ServiceSettings):
    service_name: str = "export"
    port: int = 8007
    auth_url: str = "http://auth_audit:8001"
    auth_jwt_issuer: str = "scientific-tangle-auth"
    auth_jwt_audience: str = "scientific-tangle-api"
    auth_jwks_cache_seconds: int = 300
    auth_clock_skew_seconds: int = 30
    model_url: str = "http://model:8006"
    minio_endpoint: str = "minio:9000"
    minio_secure: bool = False
    exports_bucket: str = "exports"
    export_job_ttl_seconds: int = 30 * 24 * 3600
    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")


settings = Settings()
