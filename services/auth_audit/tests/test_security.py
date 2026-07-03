from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from app.db.models import Role
from app.service.security import (
    InvalidAccessTokenError,
    KeyStore,
    PasswordManager,
    TokenManager,
    create_refresh_token,
    hash_refresh_token,
)


def test_password_hashing_and_verification() -> None:
    manager = PasswordManager()
    password_hash = manager.hash("a-secret-password")

    assert "a-secret-password" not in password_hash
    assert manager.verify("a-secret-password", password_hash)
    assert not manager.verify("wrong-password", password_hash)


def test_access_token_round_trip(settings) -> None:
    manager = TokenManager(settings, KeyStore(settings))
    user_id = uuid4()

    token, expires_in = manager.create_access_token(user_id, Role.RESEARCHER)
    claims = manager.decode_access_token(token)

    assert expires_in == 900
    assert claims.sub == user_id
    assert claims.role == Role.RESEARCHER
    assert claims.type == "access"


@pytest.mark.parametrize("changed_claim", ["iss", "aud", "type"])
def test_access_token_rejects_invalid_claim(settings, changed_claim: str) -> None:
    key_store = KeyStore(settings)
    now = datetime.now(UTC)
    payload = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "sub": str(uuid4()),
        "iat": now,
        "nbf": now,
        "exp": now + timedelta(minutes=5),
        "jti": str(uuid4()),
        "type": "access",
        "role": Role.ADMIN.value,
    }
    payload[changed_claim] = "invalid"
    token = jwt.encode(
        payload,
        key_store.private_key,
        algorithm="RS256",
        headers={"kid": settings.jwt_key_id},
    )

    with pytest.raises(InvalidAccessTokenError):
        TokenManager(settings, key_store).decode_access_token(token)


def test_access_token_rejects_missing_expiry(settings) -> None:
    key_store = KeyStore(settings)
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "sub": str(uuid4()),
            "iat": now,
            "nbf": now,
            "jti": str(uuid4()),
            "type": "access",
            "role": Role.ADMIN.value,
        },
        key_store.private_key,
        algorithm="RS256",
        headers={"kid": settings.jwt_key_id},
    )

    with pytest.raises(InvalidAccessTokenError):
        TokenManager(settings, key_store).decode_access_token(token)


def test_access_token_rejects_wrong_signature(settings) -> None:
    token_manager = TokenManager(settings, KeyStore(settings))
    foreign_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "iss": settings.jwt_issuer,
            "aud": settings.jwt_audience,
            "sub": str(uuid4()),
            "iat": now,
            "nbf": now,
            "exp": now + timedelta(minutes=5),
            "jti": str(uuid4()),
            "type": "access",
            "role": Role.ADMIN.value,
        },
        foreign_key,
        algorithm="RS256",
        headers={"kid": settings.jwt_key_id},
    )

    with pytest.raises(InvalidAccessTokenError):
        token_manager.decode_access_token(token)


def test_refresh_tokens_are_random_and_hashed() -> None:
    first = create_refresh_token()
    second = create_refresh_token()

    assert first != second
    assert len(hash_refresh_token(first)) == 64
    assert first not in hash_refresh_token(first)
