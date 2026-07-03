from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}


@router.get("/ready")
async def ready():
    return {"ready": True, "service": settings.service_name}
