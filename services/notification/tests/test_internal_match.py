import httpx
import pytest

from tests.conftest import FakeInterest


@pytest.mark.asyncio
async def test_internal_match_requires_token(client) -> None:
    response = await client.post(
        "/internal/v1/match",
        headers={"X-Internal-Service-Token": "wrong-token"},
        json={
            "user_id": "00000000-0000-0000-0000-000000000001",
            "document_id": "document-1",
            "artifacts": [],
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_internal_match_creates_interest_match(client, fake_repository, test_app) -> None:
    from uuid import uuid4

    fake_repository.interest = FakeInterest(
        "никель",
        {
            "interests": [
                {"label": "materials", "weight": 0.8, "source_terms": ["никель"]}
            ]
        },
    )

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

    test_app.state.http_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

    user_id = uuid4()
    response = await client.post(
        "/internal/v1/match",
        json={
            "user_id": str(user_id),
            "document_id": "nickel_report.pdf",
            "artifacts": [
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
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 1
    assert payload[0]["type"] == "interest_match"
    assert payload[0]["reference_id"] == "nickel_report.pdf"
    assert len(test_app.state.test_workflow_repository.created) == 1
