import asyncio
from typing import Annotated

import pytest
from conftest import FakeAuthRepository
from fastapi import Depends
from httpx import ASGITransport, AsyncClient

from app.api.factory import create_app
from app.core.dependencies import require_roles
from infra.postgres.auth_audit_db import Role, User
from app.service.security import hash_refresh_token

AdminUserDependency = Annotated[User, Depends(require_roles(Role.ADMIN))]


async def login(
    client: AsyncClient,
    identifier: str = " Researcher ",
    password: str = "correct-password",
) -> dict:
    response = await client.post(
        "/api/auth/login",
        json={"identifier": identifier, "password": password},
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
        json={"identifier": "missing", "password": "do-not-leak-this"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
    assert "missing" not in response.text
    assert "do-not-leak-this" not in response.text
    assert response.headers["www-authenticate"] == "Bearer"


async def test_inactive_user_cannot_login(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/login",
        json={"identifier": "inactive", "password": "correct-password"},
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
    assert "auth_audit_http_requests_total" in metrics.text


async def test_validation_error_is_normalized(client: AsyncClient) -> None:
    response = await client.post("/api/auth/login", json={"identifier": ""})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.headers["x-request-id"] == response.json()["error"]["request_id"]


async def test_register_normalizes_identity_and_signs_in(
    client: AsyncClient, repository: FakeAuthRepository
) -> None:
    response = await client.post(
        "/api/auth/register",
        headers={"Origin": "https://ui.example.test"},
        json={
            "username": "New.User",
            "email": "New.User@Example.com",
            "password": "Password1",
        },
    )

    assert response.status_code == 201
    assert response.json()["user"]["username"] == "new.user"
    assert response.json()["user"]["email"] == "new.user@example.com"
    assert response.json()["user"]["role"] == "external_partner"
    assert client.cookies.get("refresh_token") is not None
    stored = await repository.get_user_by_username("new.user")
    assert stored is not None
    assert "Password1" not in stored.password_hash


async def test_register_rejects_duplicates_and_role_injection(client: AsyncClient) -> None:
    duplicate = await client.post(
        "/api/auth/register",
        json={
            "username": "researcher",
            "email": "other@example.com",
            "password": "Password1",
        },
    )
    injected = await client.post(
        "/api/auth/register",
        json={
            "username": "another",
            "email": "another@example.com",
            "password": "Password1",
            "role": "admin",
        },
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "IDENTITY_ALREADY_EXISTS"
    assert injected.status_code == 422


@pytest.mark.parametrize(
    "password",
    ["Short1A", "lowercase1", "UPPERCASE1", "NoDigitsHere"],
)
async def test_register_enforces_password_policy(client: AsyncClient, password: str) -> None:
    response = await client.post(
        "/api/auth/register",
        json={"username": "newuser", "email": "new@example.com", "password": password},
    )

    assert response.status_code == 422


async def test_login_supports_email_and_legacy_seed_password(client: AsyncClient) -> None:
    payload = await login(client, "RESEARCHER@EXAMPLE.COM", "correct-password")

    assert payload["user"]["username"] == "researcher"


async def test_profile_update_requires_password_and_detects_conflict(client: AsyncClient) -> None:
    token = (await login(client))["access_token"]
    headers = {
        "Authorization": f"Bearer {token}",
        "Origin": "https://ui.example.test",
    }
    denied = await client.patch(
        "/api/auth/me",
        headers=headers,
        json={"current_password": "wrong", "username": "renamed"},
    )
    conflict = await client.patch(
        "/api/auth/me",
        headers=headers,
        json={"current_password": "correct-password", "email": "admin@example.com"},
    )
    updated = await client.patch(
        "/api/auth/me",
        headers=headers,
        json={
            "current_password": "correct-password",
            "username": "Renamed.User",
            "email": "Renamed@Example.com",
        },
    )

    assert denied.status_code == 401
    assert conflict.status_code == 409
    assert updated.status_code == 200
    assert updated.json()["username"] == "renamed.user"
    assert updated.json()["email"] == "renamed@example.com"


async def test_password_change_revokes_old_refresh_and_returns_new_session(
    client: AsyncClient, repository: FakeAuthRepository
) -> None:
    payload = await login(client)
    access_token = payload["access_token"]
    old_refresh = client.cookies.get("refresh_token")
    response = await client.post(
        "/api/auth/change-password",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Origin": "https://ui.example.test",
        },
        json={"current_password": "correct-password", "new_password": "NewPassword1"},
    )

    assert response.status_code == 200
    assert client.cookies.get("refresh_token") != old_refresh
    assert repository.sessions[hash_refresh_token(old_refresh)].revoked_at is not None
    assert (await login(client, "researcher", "NewPassword1"))["user"]["username"] == "researcher"


async def test_logout_all_revokes_sessions(
    client: AsyncClient, repository: FakeAuthRepository
) -> None:
    payload = await login(client)
    access_token = payload["access_token"]
    refresh_token = client.cookies.get("refresh_token")
    response = await client.post(
        "/api/auth/logout-all",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Origin": "https://ui.example.test",
        },
    )

    assert response.status_code == 204
    assert client.cookies.get("refresh_token") is None
    assert repository.sessions[hash_refresh_token(refresh_token)].revoked_at is not None


async def test_deactivate_account_revokes_access_to_me(client: AsyncClient) -> None:
    payload = await login(client)
    access_token = payload["access_token"]
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Origin": "https://ui.example.test",
    }
    response = await client.request(
        "DELETE",
        "/api/auth/me",
        headers=headers,
        json={"current_password": "correct-password"},
    )
    me = await client.get("/api/auth/me", headers={"Authorization": f"Bearer {access_token}"})

    assert response.status_code == 204
    assert me.status_code == 401


async def test_admin_lists_and_updates_users(client: AsyncClient) -> None:
    admin_token = (await login(client, "admin", "AdminPassword1"))["access_token"]
    headers = {"Authorization": f"Bearer {admin_token}"}
    listing = await client.get("/api/auth/users?limit=2&offset=0", headers=headers)
    researcher_id = next(
        user["id"] for user in listing.json()["items"] if user["username"] == "researcher"
    )
    updated = await client.patch(
        f"/api/auth/users/{researcher_id}",
        headers={**headers, "Origin": "https://ui.example.test"},
        json={"role": "analyst", "is_active": False},
    )

    assert listing.status_code == 200
    assert listing.json()["total"] == 3
    assert updated.status_code == 200
    assert updated.json()["role"] == "analyst"
    assert not updated.json()["is_active"]


async def test_non_admin_cannot_manage_users(client: AsyncClient) -> None:
    token = (await login(client))["access_token"]

    response = await client.get(
        "/api/auth/users", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 403
