import asyncio

import httpx
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings

router = APIRouter(tags=["health"])

PEER_SERVICES = {
    "auth_audit": "http://auth_audit:8001",
    "orchestrator": "http://orchestrator:8002",
    "ingestion": "http://ingestion:8003",
    "knowledge": "http://knowledge:8004",
    "retrieval": "http://retrieval:8005",
    "model": "http://model:8006",
    "export": "http://export:8007",
    "notification": "http://notification:8008",
}


async def _probe(name: str, base_url: str) -> dict:
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                return {"service": name, "status": "ok", "url": base_url}
            return {
                "service": name,
                "status": "degraded",
                "url": base_url,
                "http_status": response.status_code,
            }
    except Exception as exc:
        return {"service": name, "status": "down", "url": base_url, "error": str(exc)}


@router.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}


@router.get("/ready")
async def ready():
    return {"ready": True, "service": settings.service_name}


@router.get("/health/all")
async def health_all():
    results = await asyncio.gather(
        *(_probe(name, url) for name, url in PEER_SERVICES.items())
    )
    overall = "ok"
    if any(item["status"] == "down" for item in results):
        overall = "down"
    elif any(item["status"] == "degraded" for item in results):
        overall = "degraded"
    payload = {
        "status": overall,
        "service": settings.service_name,
        "peers": results,
    }
    status_code = 200 if overall == "ok" else 503
    return JSONResponse(content=payload, status_code=status_code)
