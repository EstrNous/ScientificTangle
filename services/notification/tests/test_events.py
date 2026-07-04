import pytest

from infra.postgres.notification_db.repository import NotificationData


@pytest.mark.asyncio
async def test_internal_create_event_requires_token(client, fake_repository, principal) -> None:
    response = await client.post(
        "/internal/v1/events",
        headers={"X-Internal-Service-Token": "wrong-token"},
        json={
            "user_id": str(principal.user_id),
            "type": "conflict_detected",
            "message": "Обнаружено противоречие",
        },
    )
    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"


@pytest.mark.asyncio
async def test_internal_create_event(client, fake_repository, principal) -> None:
    response = await client.post(
        "/internal/v1/events",
        json={
            "user_id": str(principal.user_id),
            "type": "conflict_detected",
            "message": "Обнаружено противоречие",
            "reference_id": "run-42",
            "reference_type": "query_run",
            "match_score": 1.0,
            "match_reason": "query_conflict_detected",
            "match_payload": {"conflict_count": 2, "query_run_id": "run-42"},
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["type"] == "conflict_detected"
    assert payload["reference_id"] == "run-42"
    assert len(fake_repository.created_events) == 1
    assert fake_repository.created_events[0].type == "conflict_detected"
