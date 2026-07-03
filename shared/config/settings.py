from pydantic_settings import BaseSettings, SettingsConfigDict


class ServiceSettings(BaseSettings):
    service_name: str = "unknown"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"
    redis_url: str = "redis://redis:6379/0"
    postgres_url: str = "postgresql+asyncpg://st_user:st_pass@postgres:5432/scientific_tangle"
    neo4j_url: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "neo4j_pass"
    qdrant_url: str = "http://qdrant:6333"
    minio_url: str = "http://minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin123"

    model_config = SettingsConfigDict(env_prefix="", env_file=".env")
