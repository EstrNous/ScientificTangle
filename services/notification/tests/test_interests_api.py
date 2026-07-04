import pytest


@pytest.mark.asyncio
async def test_get_interests_empty(client, fake_repository) -> None:
    response = await client.get("/interests")
    assert response.status_code == 200
    payload = response.json()
    assert payload["interests"] == []
    assert payload["raw_text"] in (None, "")


@pytest.mark.asyncio
async def test_put_interests_persists_structured_payload(client, fake_repository, principal) -> None:
    response = await client.put(
        "/interests",
        json={
            "raw_text": "никель, флотация",
            "interests": [
                {"label": "materials", "weight": 0.8, "source_terms": ["никель"]}
            ],
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["raw_text"] == "никель, флотация"
    assert payload["interests"][0]["label"] == "materials"
    assert fake_repository.interest is not None
    assert fake_repository.interest.extracted_entities["interests"][0]["label"] == "materials"
