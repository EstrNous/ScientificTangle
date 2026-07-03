from typing import Any, cast

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
from infra.postgres.auth_audit_db import HealthResponse
from sqlalchemy import text

from ..service.security import KeyStore

router = APIRouter()


@router.get("/.well-known/jwks.json")
async def jwks(request: Request) -> dict[str, list[dict[str, Any]]]:
    key_store = cast(KeyStore, request.app.state.key_store)
    return key_store.jwks()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse()


@router.get("/ready", response_model=HealthResponse)
async def ready(request: Request) -> Response:
    try:
        request.app.state.key_store.validate_pair()
        if request.app.state.repository is None:
            async with request.app.state.session_factory() as session:
                await session.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unavailable"})
    return JSONResponse(content=HealthResponse().model_dump())
