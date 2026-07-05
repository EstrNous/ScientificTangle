from fastapi import APIRouter, Request, Response, status

from ..core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}


@router.get("/ready")
async def ready(request: Request, response: Response):
    is_ready = request.app.state.storage_adapter.is_ready
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return {"ready": is_ready, "service": settings.service_name}
