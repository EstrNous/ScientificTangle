import asyncio
from uuid import uuid4

import httpx
from app.service.matching_service import MatchingService

from tests.conftest import FakeInterest, FakeRepository


class FakeWorkflowRepository:
    def __init__(self) -> None:
        self.created: list = []

    async def create_notification_with_match(self, user_id, *, type, message, reference_id, reference_type, match):
        from tests.conftest import FakeNotification

        note = FakeNotification()
        note.type = type
        note.message = message
        note.reference_id = reference_id
        note.reference_type = reference_type
        note.match_score = match.match_score
        note.match_payload = match.match_payload
        self.created.append(note)
        return note, None


def test_match_and_notify_creates_interest_match() -> None:
    repository = FakeRepository()
    repository.interest = FakeInterest(
        "никель",
        {
            "interests": [
                {"label": "materials", "weight": 0.8, "source_terms": ["никель"]}
            ]
        },
    )
    workflow = FakeWorkflowRepository()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/notifications/match"
        return httpx.Response(
            200,
            json={
                "matches": [
                    {
                        "interest_label": "materials",
                        "artifact_id": "artifact-1",
                        "score": 0.81,
                        "reason": "никель",
                    }
                ]
            },
        )

    async def run() -> None:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = MatchingService(repository, workflow, client=client, model_url="http://model")
            created = await service.match_and_notify(
                uuid4(),
                "nickel_report.pdf",
                [
                    {
                        "id": "artifact-1",
                        "kind": "entity",
                        "value": "никель",
                        "status": "confirmed",
                        "confidence": 0.9,
                        "metadata": {},
                        "reason_codes": [],
                    }
                ],
            )
            assert len(created) == 1
            assert created[0].type == "interest_match"

    asyncio.run(run())
    assert len(workflow.created) == 1
