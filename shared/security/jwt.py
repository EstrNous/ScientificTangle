import asyncio
import time
from dataclasses import dataclass
from uuid import UUID

import httpx
import jwt

from shared.contracts import UserRole


class AuthenticationError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    user_id: UUID
    role: UserRole
    token_id: UUID


class JWKSValidator:
    required_claims = ["iss", "aud", "sub", "iat", "nbf", "exp", "jti", "type", "role"]

    def __init__(
        self,
        auth_url: str,
        issuer: str,
        audience: str,
        cache_seconds: int = 300,
        clock_skew_seconds: int = 30,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._jwks_url = f"{auth_url.rstrip('/')}/.well-known/jwks.json"
        self._issuer = issuer
        self._audience = audience
        self._cache_seconds = cache_seconds
        self._clock_skew_seconds = clock_skew_seconds
        self._client = client or httpx.AsyncClient(timeout=5.0)
        self._owns_client = client is None
        self._keys: dict[str, jwt.PyJWK] = {}
        self._cache_expires_at = 0.0
        self._lock = asyncio.Lock()

    async def validate(self, token: str) -> AuthenticatedPrincipal:
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
                raise AuthenticationError
            key = await self._get_key(header["kid"])
            payload = jwt.decode(
                token,
                key.key,
                algorithms=["RS256"],
                audience=self._audience,
                issuer=self._issuer,
                leeway=self._clock_skew_seconds,
                options={"require": self.required_claims},
            )
            if payload["type"] != "access":
                raise AuthenticationError
            return AuthenticatedPrincipal(
                user_id=UUID(payload["sub"]),
                role=UserRole(payload["role"]),
                token_id=UUID(payload["jti"]),
            )
        except (jwt.PyJWTError, KeyError, TypeError, ValueError, AuthenticationError) as error:
            raise AuthenticationError from error

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def _get_key(self, key_id: str) -> jwt.PyJWK:
        now = time.monotonic()
        if now >= self._cache_expires_at:
            await self._refresh_keys()
        key = self._keys.get(key_id)
        if key is None:
            await self._refresh_keys(force=True)
            key = self._keys.get(key_id)
        if key is None:
            raise AuthenticationError
        return key

    async def _refresh_keys(self, force: bool = False) -> None:
        async with self._lock:
            now = time.monotonic()
            if not force and self._keys and now < self._cache_expires_at:
                return
            try:
                response = await self._client.get(self._jwks_url)
                response.raise_for_status()
                payload = response.json()
                keys = payload.get("keys")
                if not isinstance(keys, list):
                    raise AuthenticationError
                parsed = {
                    item["kid"]: jwt.PyJWK.from_dict(item)
                    for item in keys
                    if isinstance(item, dict) and isinstance(item.get("kid"), str)
                }
                if not parsed:
                    raise AuthenticationError
                self._keys = parsed
                self._cache_expires_at = now + self._cache_seconds
            except (httpx.HTTPError, ValueError, TypeError, KeyError) as error:
                raise AuthenticationError from error


def get_bearer_token(authorization: str | None) -> str:
    if authorization is None:
        raise AuthenticationError
    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token.strip():
        raise AuthenticationError
    return token.strip()
