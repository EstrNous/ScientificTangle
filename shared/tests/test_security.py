import asyncio
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm

from shared.contracts import UserRole
from shared.security import AuthenticationError, JWKSValidator, get_bearer_token


def make_token(
    private_key: rsa.RSAPrivateKey,
    key_id: str = "main-key",
    audience: str = "scientific-tangle",
    expires_delta: timedelta = timedelta(minutes=5),
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "iss": "auth_service",
            "aud": audience,
            "sub": str(uuid4()),
            "iat": now,
            "nbf": now,
            "exp": now + expires_delta,
            "jti": str(uuid4()),
            "type": "access",
            "role": "researcher",
        },
        private_key,
        algorithm="RS256",
        headers={"kid": key_id},
    )


def make_validator(
    private_key: rsa.RSAPrivateKey,
) -> tuple[JWKSValidator, httpx.AsyncClient]:
    public_jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk.update({"kid": "main-key", "alg": "RS256", "use": "sig"})

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"keys": [public_jwk]})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    validator = JWKSValidator(
        auth_url="http://auth",
        issuer="auth_service",
        audience="scientific-tangle",
        cache_seconds=300,
        clock_skew_seconds=0,
        client=client,
    )
    return validator, client


def test_valid_token_returns_principal() -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    validator, client = make_validator(private_key)

    async def run() -> None:
        principal = await validator.validate(make_token(private_key))
        assert principal.role == UserRole.RESEARCHER
        await client.aclose()

    asyncio.run(run())


@pytest.mark.parametrize(
    ("key_id", "audience", "expires_delta"),
    [
        ("unknown-key", "scientific-tangle", timedelta(minutes=5)),
        ("main-key", "wrong-audience", timedelta(minutes=5)),
        ("main-key", "scientific-tangle", timedelta(seconds=-1)),
    ],
)
def test_invalid_token_is_rejected(
    key_id: str,
    audience: str,
    expires_delta: timedelta,
) -> None:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    validator, client = make_validator(private_key)

    async def run() -> None:
        with pytest.raises(AuthenticationError):
            await validator.validate(
                make_token(
                    private_key,
                    key_id=key_id,
                    audience=audience,
                    expires_delta=expires_delta,
                )
            )
        await client.aclose()

    asyncio.run(run())


@pytest.mark.parametrize("value", [None, "", "Basic abc", "Bearer", "Bearer   "])
def test_invalid_authorization_header_is_rejected(value: str | None) -> None:
    with pytest.raises(AuthenticationError):
        get_bearer_token(value)
