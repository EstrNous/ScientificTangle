import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_create_session_requires_auth(chat_test_app) -> None:
    transport = ASGITransport(app=chat_test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/chat/sessions", json={"title": "Новый запрос"})

    assert response.status_code == 401
    assert response.json()["code"] == "authentication_required"


@pytest.mark.asyncio
async def test_create_session_rejects_empty_title(chat_client) -> None:
    response = await chat_client.post("/chat/sessions", json={"title": ""})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_session_returns_201_for_new_chat_button(
    chat_client,
    fake_chat_repository,
) -> None:
    response = await chat_client.post(
        "/chat/sessions",
        json={"title": "Новый запрос"},
        headers={"X-Request-ID": "chat-create-1"},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["title"] == "Новый запрос"
    assert payload["id"]
    assert payload["created_at"]
    assert payload["updated_at"]
    assert len(fake_chat_repository.sessions) == 1
    assert fake_chat_repository.sessions[0].title == "Новый запрос"


@pytest.mark.asyncio
async def test_create_session_appears_in_list(chat_client) -> None:
    created = await chat_client.post("/chat/sessions", json={"title": "Новый запрос"})
    assert created.status_code == 201
    session_id = created.json()["id"]

    listing = await chat_client.get("/chat/sessions")
    assert listing.status_code == 200
    sessions = listing.json()
    assert len(sessions) == 1
    assert sessions[0]["id"] == session_id
    assert sessions[0]["title"] == "Новый запрос"


@pytest.mark.asyncio
async def test_create_session_rejects_whitespace_only_title(chat_client) -> None:
    response = await chat_client.post("/chat/sessions", json={"title": "   "})

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_session_trims_title(chat_client) -> None:
    response = await chat_client.post("/chat/sessions", json={"title": "  Запрос  "})

    assert response.status_code == 201
    assert response.json()["title"] == "Запрос"


@pytest.mark.asyncio
async def test_send_message_rejects_whitespace_only_content(chat_client) -> None:
    created = await chat_client.post("/chat/sessions", json={"title": "Тест"})
    session_id = created.json()["id"]

    response = await chat_client.post(
        f"/chat/sessions/{session_id}/messages",
        json={"content": "   "},
    )

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_session_returns_204(chat_client, fake_chat_repository) -> None:
    created = await chat_client.post("/chat/sessions", json={"title": "Удалить"})
    session_id = created.json()["id"]

    response = await chat_client.delete(f"/chat/sessions/{session_id}")

    assert response.status_code == 204
    assert len(fake_chat_repository.sessions) == 0


@pytest.mark.asyncio
async def test_delete_session_returns_404_for_unknown(chat_client) -> None:
    from uuid import uuid4

    response = await chat_client.delete(f"/chat/sessions/{uuid4()}")

    assert response.status_code == 404
    assert response.json()["code"] == "session_not_found"


@pytest.mark.asyncio
async def test_list_messages_returns_404_for_unknown_session(chat_client) -> None:
    from uuid import uuid4

    response = await chat_client.get(f"/chat/sessions/{uuid4()}/messages")

    assert response.status_code == 404
    assert response.json()["code"] == "session_not_found"
