import asyncio
from datetime import UTC, datetime
from uuid import uuid4

import httpx
from app.service.service import GatewayService
from shared.contracts import ReviewDecisionResult, ReviewQueuePayload


def test_get_review_queue_validates_contract() -> None:
    item_id = uuid4()
    created_at = datetime.now(UTC).isoformat()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/review/queue"
        assert request.headers["Authorization"] == "Bearer token"
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": str(item_id),
                        "document_id": "doc-1",
                        "source_span_id": "span-1",
                        "status": "pending",
                        "priority": "medium",
                        "payload": {"candidate_type": "substance"},
                        "created_at": created_at,
                    }
                ],
                "total_found": 1,
                "warnings": [],
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GatewayService(client, "http://orchestrator", 1024)
            payload = await service.get_review_queue("Bearer token", "req-1", "pending", 20)
            validated = ReviewQueuePayload.model_validate(payload)
            assert validated.total_found == 1
            assert validated.items[0].document_id == "doc-1"

    asyncio.run(run())


def test_review_decision_validates_contract() -> None:
    item_id = uuid4()
    decided_by = uuid4()
    decided_at = datetime.now(UTC).isoformat()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/review/decisions"
        return httpx.Response(
            200,
            json={
                "item_id": str(item_id),
                "status": "approved",
                "decided_by": str(decided_by),
                "decided_at": decided_at,
                "warnings": [],
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GatewayService(client, "http://orchestrator", 1024)
            payload = await service.review_decision(
                {
                    "item_id": str(item_id),
                    "decision": "approve",
                    "reason": "ok",
                    "source_span_ids": ["span-1"],
                },
                "Bearer token",
                "req-2",
            )
            validated = ReviewDecisionResult.model_validate(payload)
            assert validated.status == "approved"
            assert validated.item_id == item_id

    asyncio.run(run())
