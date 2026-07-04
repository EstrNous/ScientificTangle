from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from shared.contracts import UserRole
from shared.security import AuthenticatedPrincipal
from shared.web import (
    AuthorizedContext,
    RateLimitRule,
    ServiceError,
    forwarded_auth,
    install_error_handlers,
    install_rate_limit_middleware,
    request_id_middleware,
    require_forwarded_auth,
    require_internal_service,
    require_principal,
)


def make_app() -> FastAPI:
    app = FastAPI()
    app.middleware("http")(request_id_middleware)
    install_error_handlers(app)
    app.state.internal_service_token = "test-internal-token"

    @app.get("/failure")
    async def failure() -> None:
        raise ServiceError(409, "known_failure", "Known failure")

    @app.get("/protected")
    async def protected(
        principal: AuthenticatedPrincipal = Depends(require_principal),
    ) -> dict[str, str]:
        return {"user_id": str(principal.user_id)}

    @app.get("/internal")
    async def internal(_: None = Depends(require_internal_service)) -> dict[str, str]:
        return {"status": "ok"}

    return app


def test_service_error_and_request_id_have_stable_shape() -> None:
    with TestClient(make_app()) as client:
        response = client.get("/failure", headers={"X-Request-ID": "request-1"})

    assert response.status_code == 409
    assert response.headers["X-Request-ID"] == "request-1"
    assert response.json() == {
        "code": "known_failure",
        "message": "Known failure",
        "request_id": "request-1",
    }


def test_missing_bearer_token_has_normalized_error() -> None:
    with TestClient(make_app()) as client:
        response = client.get("/protected")

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_internal_service_token_is_required() -> None:
    with TestClient(make_app()) as client:
        response = client.get("/internal")

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"


def test_internal_service_token_accepts_valid_header() -> None:
    with TestClient(make_app()) as client:
        response = client.get("/internal", headers={"X-Internal-Service-Token": "test-internal-token"})

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_internal_service_token_rejects_invalid_header() -> None:
    with TestClient(make_app()) as client:
        response = client.get("/internal", headers={"X-Internal-Service-Token": "wrong-token"})

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"


def test_rate_limit_returns_normalized_error_and_headers() -> None:
    app = FastAPI()
    install_rate_limit_middleware(
        app,
        enabled=True,
        redis_url="redis://redis:6379/0",
        service_name="test",
        rules=(RateLimitRule(name="default", limit=1),),
        use_redis=False,
    )
    app.middleware("http")(request_id_middleware)

    @app.get("/limited")
    async def limited() -> dict[str, bool]:
        return {"ok": True}

    with TestClient(app) as client:
        first = client.get("/limited", headers={"X-Request-ID": "request-1"})
        second = client.get("/limited", headers={"X-Request-ID": "request-2"})

    assert first.status_code == 200
    assert first.headers["X-RateLimit-Limit"] == "1"
    assert first.headers["X-RateLimit-Remaining"] == "0"
    assert second.status_code == 429
    assert second.headers["Retry-After"] == "60"
    assert second.json() == {
        "code": "rate_limited",
        "message": "Too many requests",
        "request_id": "request-2",
    }


def test_rate_limit_excludes_operational_paths() -> None:
    app = FastAPI()
    install_rate_limit_middleware(
        app,
        enabled=True,
        redis_url="redis://redis:6379/0",
        service_name="test",
        rules=(RateLimitRule(name="default", limit=1),),
        excluded_paths=("/health",),
        use_redis=False,
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    with TestClient(app) as client:
        responses = [client.get("/health") for _ in range(3)]

    assert [response.status_code for response in responses] == [200, 200, 200]


def test_forwarded_auth_exposes_authorization_after_require_principal() -> None:
    principal = AuthenticatedPrincipal(
        user_id=uuid4(),
        role=UserRole.ADMIN,
        token_id=uuid4(),
    )
    app = FastAPI()
    app.middleware("http")(request_id_middleware)
    install_error_handlers(app)
    app.state.jwt_validator = AsyncMock()
    app.state.jwt_validator.validate = AsyncMock(return_value=principal)

    @app.post("/echo-auth")
    async def echo_auth(
        _: AuthenticatedPrincipal = Depends(require_principal),
    ) -> dict[str, str]:
        authorization, request_id = forwarded_auth()
        return {"authorization": authorization, "request_id": request_id}

    with TestClient(app) as client:
        response = client.post(
            "/echo-auth",
            headers={"Authorization": "Bearer test-token", "X-Request-ID": "req-auth"},
            json={"content": "nickel"},
        )

    assert response.status_code == 200
    assert response.json()["authorization"] == "Bearer test-token"
    assert response.json()["request_id"] == "req-auth"


def test_require_forwarded_auth_returns_authorized_context() -> None:
    principal = AuthenticatedPrincipal(
        user_id=uuid4(),
        role=UserRole.ADMIN,
        token_id=uuid4(),
    )
    app = FastAPI()
    app.middleware("http")(request_id_middleware)
    install_error_handlers(app)
    app.state.jwt_validator = AsyncMock()
    app.state.jwt_validator.validate = AsyncMock(return_value=principal)

    @app.post("/auth-context")
    async def auth_context(
        auth: AuthorizedContext = Depends(require_forwarded_auth),
    ) -> dict[str, str]:
        return {
            "user_id": str(auth.principal.user_id),
            "authorization": auth.authorization,
            "request_id": auth.request_id,
        }

    with TestClient(app) as client:
        response = client.post(
            "/auth-context",
            headers={"Authorization": "Bearer ctx-token", "X-Request-ID": "req-ctx"},
            json={"question": "nickel"},
        )

    assert response.status_code == 200
    assert response.json()["authorization"] == "Bearer ctx-token"
    assert response.json()["request_id"] == "req-ctx"
