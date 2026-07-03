from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict

from shared.config.settings import ServiceSettings


class Settings(ServiceSettings):
    model_config = SettingsConfigDict(
        env_prefix="AUTH_",
        case_sensitive=False,
        extra="ignore",
    )

    service_name: str = "auth_audit"
    environment: str = "production"

    port: int = 8001

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/scientific_tangle"

    jwt_issuer: str = "scientific-tangle-auth"
    jwt_audience: str = "scientific-tangle-api"
    jwt_key_id: str = "auth-key-1"

    jwt_private_key: SecretStr | None = None
    jwt_public_key: str | None = None
    jwt_private_key_path: Path = Path("/run/secrets/auth_jwt_private.pem")
    jwt_public_key_path: Path = Path("/run/secrets/auth_jwt_public.pem")

    access_token_minutes: int = 15
    refresh_token_days: int = 7
    clock_skew_seconds: int = 30

    refresh_cookie_name: str = "refresh_token"
    refresh_cookie_secure: bool = True

    allowed_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def origin_allowlist(self) -> frozenset[str]:
        return frozenset(
            origin.strip()
            for origin in self.allowed_origins.split(",")
            if origin.strip()
        )


settings = Settings()