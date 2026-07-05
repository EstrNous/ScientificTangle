from adapters.neo4j_adapter import Neo4jKnowledgeAdapter
from fastapi import APIRouter, Request

from shared.utils.request_id import generate_request_id

from ..core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health():
    return {"status": "ok", "service": settings.service_name}


@router.get("/ready")
async def ready(app_request: Request):
    adapter: Neo4jKnowledgeAdapter | None = getattr(app_request.app.state, "neo4j_adapter", None)
    if adapter is None:
        return {"ready": False, "service": settings.service_name, "neo4j": "missing_adapter"}
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    neo4j_ok = await adapter.ping(request_id=request_id)
    return {
        "ready": neo4j_ok,
        "service": settings.service_name,
        "neo4j": "ok" if neo4j_ok else "degraded",
    }
