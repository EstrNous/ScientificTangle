from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from ..core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}


@router.get("/ready")
async def ready(request: Request):
    try:
        async with request.app.state.session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"ready": True, "service": settings.service_name}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"ready": False, "service": settings.service_name, "error": str(exc)},
        )
