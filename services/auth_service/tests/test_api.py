import asyncio
from typing import Annotated

from conftest import FakeAuthRepository
from fastapi import Depends
from httpx import ASGITransport, AsyncClient

from app.dependencies import require_roles
from app.models import Role, User
from app.security import hash_refresh_token
from app.web import create_app

AdminUserDependency = Annotated[User, Depends(require_roles(Role.ADMIN))]


async def login(client: AsyncClient) -> dict:
    response = await client.post(
        "/api/auth/login",
        json={"username": " Researcher ", "password": "correct-password"},
    )
    assert response.status_code == 200
    return response.json()


async def test_login_sets_secure_refresh_cookie(client: AsyncClient) -> None:
    payload = await login(client)
    cookie = client.cookies.get("refresh_token")
    set_cookie = client.cookies.jar._cookies["testserver.local"]["/api/auth"]["refresh_token"]

    assert payload["token_type"] == "bearer"
    assert payload["expires_in"] == 900
    assert payload["user"]["role"] == "researcher"
    assert cookie is not None
    assert set_cookie.secure
    assert set_cookie.has_nonstandard_attr("HttpOnly")
    assert set_cookie.get_nonstandard_attr("SameSite") == "strict"


async def test_invalid_login_is_generic_and_does_not_leak_credentials(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/login",
        json={"username": "missing", "password": "do-not-leak-this"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert "missing" not in response.text
    assert "do-not-leak-this" not in response.text
    assert response.headers["www-authenticate"] == "Bearer"


async def test_inactive_user_cannot_login(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/login",
        json={"username": "inactive", "password": "correct-password"},
    )

    assert response.status_code == 401


async def test_me_returns_authenticated_user(client: AsyncClient) -> None:
    payload = await login(client)
    response = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {payload['access_token']}"}
    )

    assert response.status_code == 200
    assert response.json()["username"] == "researcher"


async def test_refresh_rotates_token_and_replay_revokes_family(
    client: AsyncClient, repository: FakeAuthRepository
) -> None:
    await login(client)
    old_token = client.cookies.get("refresh_token")
    refresh_response = await client.post(
        "/api/auth/refresh", headers={"Origin": "https://ui.example.test"}
    )
    new_token = client.cookies.get("refresh_token")

    assert refresh_response.status_code == 200
    assert new_token != old_token
    client.cookies.set("refresh_token", old_token, domain="testserver.local", path="/api/auth")
    replay_response = await client.post(
        "/api/auth/refresh", headers={"Origin": "https://ui.example.test"}
    )
    assert replay_response.status_code == 401
    assert repository.sessions[hash_refresh_token(new_token)].revoked_at is not None


async def test_concurrent_refresh_allows_only_one_rotation(client: AsyncClient) -> None:
    await login(client)
    token = client.cookies.get("refresh_token")

    async def refresh_once() -> int:
        client.cookies.set("refresh_token", token, domain="testserver.local", path="/api/auth")
        response = await client.post(
            "/api/auth/refresh", headers={"Origin": "https://ui.example.test"}
        )
        return response.status_code

    statuses = await asyncio.gather(refresh_once(), refresh_once())

    assert sorted(statuses) == [200, 401]


async def test_logout_revokes_session_and_clears_cookie(
    client: AsyncClient, repository: FakeAuthRepository
) -> None:
    await login(client)
    token = client.cookies.get("refresh_token")
    response = await client.post("/api/auth/logout", headers={"Origin": "https://ui.example.test"})

    assert response.status_code == 204
    assert client.cookies.get("refresh_token") is None
    assert repository.sessions[hash_refresh_token(token)].revoked_at is not None


async def test_refresh_rejects_untrusted_origin(client: AsyncClient) -> None:
    await login(client)
    response = await client.post(
        "/api/auth/refresh", headers={"Origin": "https://attacker.example"}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"


async def test_role_dependency_denies_by_default(settings, repository: FakeAuthRepository) -> None:
    app = create_app(settings=settings, repository=repository)

    @app.get("/admin-test")
    async def admin_test(user: AdminUserDependency) -> dict[str, bool]:
        return {"allowed": True}

    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="https://testserver",
    ) as local_client:
        payload = await login(local_client)
        response = await local_client.get(
            "/admin-test", headers={"Authorization": f"Bearer {payload['access_token']}"}
        )

    assert response.status_code == 403


async def test_operational_endpoints_and_jwks(client: AsyncClient) -> None:
    health = await client.get("/health")
    ready = await client.get("/ready")
    jwks = await client.get("/.well-known/jwks.json")
    metrics = await client.get("/metrics")

    assert health.json() == {"status": "ok"}
    assert ready.json() == {"status": "ok"}
    assert jwks.json()["keys"][0]["alg"] == "RS256"
    assert jwks.json()["keys"][0]["kid"] == "auth-key-1"
    assert "auth_http_requests_total" in metrics.text


async def test_validation_error_is_normalized(client: AsyncClient) -> None:
    response = await client.post("/api/auth/login", json={"username": ""})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.headers["x-request-id"] == response.json()["error"]["request_id"]
