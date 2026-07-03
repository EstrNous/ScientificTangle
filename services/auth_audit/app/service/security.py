import hashlib
import json
import secrets
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey, RSAPublicKey
from jwt.algorithms import RSAAlgorithm
from pwdlib import PasswordHash
from pydantic import BaseModel, ConfigDict

from app.core.config import Settings
from infra.postgres.auth_audit_db import Role


class InvalidAccessTokenError(Exception):
    pass


class AccessTokenClaims(BaseModel):
    model_config = ConfigDict(extra="ignore")

    iss: str
    aud: str | list[str]
    sub: UUID
    iat: datetime
    nbf: datetime
    exp: datetime
    jti: UUID
    type: str
    role: Role


class PasswordManager:
    def __init__(self) -> None:
        self._password_hash = PasswordHash.recommended()
        self.dummy_hash = self._password_hash.hash(secrets.token_urlsafe(48))

    def hash(self, password: str) -> str:
        return self._password_hash.hash(password)

    def verify(self, password: str, password_hash: str) -> bool:
        return self._password_hash.verify(password, password_hash)


class KeyStore:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._private_key: RSAPrivateKey | None = None
        self._public_key: RSAPublicKey | None = None

    def _private_pem(self) -> bytes:
        if self._settings.jwt_private_key is not None:
            return self._settings.jwt_private_key.get_secret_value().replace("\\n", "\n").encode()
        return Path(self._settings.jwt_private_key_path).read_bytes()

    def _public_pem(self) -> bytes:
        if self._settings.jwt_public_key is not None:
            return self._settings.jwt_public_key.replace("\\n", "\n").encode()
        return Path(self._settings.jwt_public_key_path).read_bytes()

    @property
    def private_key(self) -> RSAPrivateKey:
        if self._private_key is None:
            key = serialization.load_pem_private_key(self._private_pem(), password=None)
            if not isinstance(key, RSAPrivateKey):
                raise TypeError("JWT private key must be RSA")
            self._private_key = key
        return self._private_key

    @property
    def public_key(self) -> RSAPublicKey:
        if self._public_key is None:
            key = serialization.load_pem_public_key(self._public_pem())
            if not isinstance(key, RSAPublicKey):
                raise TypeError("JWT public key must be RSA")
            self._public_key = key
        return self._public_key

    def validate_pair(self) -> None:
        if self.private_key.public_key().public_numbers() != self.public_key.public_numbers():
            raise ValueError("JWT private and public keys do not match")

    def jwks(self) -> dict[str, list[dict[str, Any]]]:
        jwk = json.loads(RSAAlgorithm.to_jwk(self.public_key))
        jwk.update({"kid": self._settings.jwt_key_id, "use": "sig", "alg": "RS256"})
        return {"keys": [jwk]}


class TokenManager:
    required_claims = ["iss", "aud", "sub", "iat", "nbf", "exp", "jti", "type", "role"]

    def __init__(self, settings: Settings, key_store: KeyStore) -> None:
        self._settings = settings
        self._key_store = key_store

    def create_access_token(self, user_id: UUID, role: Role) -> tuple[str, int]:
        now = datetime.now(UTC)
        expires_at = now + timedelta(minutes=self._settings.access_token_minutes)
        payload = {
            "iss": self._settings.jwt_issuer,
            "aud": self._settings.jwt_audience,
            "sub": str(user_id),
            "iat": now,
            "nbf": now,
            "exp": expires_at,
            "jti": str(uuid4()),
            "type": "access",
            "role": role.value,
        }
        token = jwt.encode(
            payload,
            self._key_store.private_key,
            algorithm="RS256",
            headers={"kid": self._settings.jwt_key_id},
        )
        return token, self._settings.access_token_minutes * 60

    def decode_access_token(self, token: str) -> AccessTokenClaims:
        try:
            header = jwt.get_unverified_header(token)
            if header.get("kid") != self._settings.jwt_key_id:
                raise InvalidAccessTokenError
            payload = jwt.decode(
                token,
                self._key_store.public_key,
                algorithms=["RS256"],
                audience=self._settings.jwt_audience,
                issuer=self._settings.jwt_issuer,
                leeway=self._settings.clock_skew_seconds,
                options={"require": self.required_claims},
            )
            claims = AccessTokenClaims.model_validate(payload)
            if claims.type != "access":
                raise InvalidAccessTokenError
            return claims
        except (jwt.PyJWTError, ValueError, TypeError, InvalidAccessTokenError) as error:
            raise InvalidAccessTokenError from error


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
