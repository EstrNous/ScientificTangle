from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from ..core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request):
    redis_bus = getattr(request.app.state, "redis_bus", None)
    delivery_worker = getattr(request.app.state, "delivery_worker", None)
    return {
        "status": "ok",
        "service": settings.service_name,
        "redis_pubsub": {
            "enabled": settings.notification_redis_pubsub_enabled,
            "available": bool(redis_bus and redis_bus.available),
            "delivery_worker_running": bool(delivery_worker and delivery_worker.running),
        },
    }


@router.get("/ready")
async def ready(request: Request):
    try:
        async with request.app.state.session_factory() as session:
            await session.execute(text("SELECT 1"))
        redis_bus = getattr(request.app.state, "redis_bus", None)
        delivery_worker = getattr(request.app.state, "delivery_worker", None)
        if settings.notification_redis_pubsub_enabled:
            if redis_bus is None or not redis_bus.available:
                raise RuntimeError("redis pubsub unavailable")
            if delivery_worker is None or not delivery_worker.running:
                raise RuntimeError("delivery worker is not running")
        return {"ready": True, "service": settings.service_name}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"ready": False, "service": settings.service_name, "error": str(exc)},
        )
