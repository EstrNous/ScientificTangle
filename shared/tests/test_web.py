from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from shared.security import AuthenticatedPrincipal
from shared.web import (
    ServiceError,
    install_error_handlers,
    request_id_middleware,
    require_principal,
)


def make_app() -> FastAPI:
    app = FastAPI()
    app.middleware("http")(request_id_middleware)
    install_error_handlers(app)

    @app.get("/failure")
    async def failure() -> None:
        raise ServiceError(409, "known_failure", "Known failure")

    @app.get("/protected")
    async def protected(
        principal: AuthenticatedPrincipal = Depends(require_principal),
    ) -> dict[str, str]:
        return {"user_id": str(principal.user_id)}

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
