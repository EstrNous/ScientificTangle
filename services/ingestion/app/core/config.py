from shared.config.settings import ServiceSettings
from pydantic_settings import SettingsConfigDict


class Settings(ServiceSettings):
    service_name: str = "ingestion"
    port: int = 8003
    auth_url: str = "http://auth_audit:8001"
    auth_jwt_issuer: str = "scientific-tangle-auth"
    auth_jwt_audience: str = "scientific-tangle-api"
    auth_jwks_cache_seconds: int = 300
    auth_clock_skew_seconds: int = 30
    minio_endpoint: str = "minio:9000"
    minio_secure: bool = False
    source_bucket: str = "source-files"
    upload_limit_bytes: int = 100 * 1024 * 1024
    libreoffice_binary: str = "soffice"
    doc_conversion_timeout_seconds: float = 60.0
    archive_max_entries: int = 200
    archive_max_uncompressed_bytes: int = 100 * 1024 * 1024
    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")


settings = Settings()
