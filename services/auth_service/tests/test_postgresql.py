import asyncio
import os
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

from app.database import create_database
from app.models import RefreshSession, Role, User
from app.repository import (
    RefreshSessionData,
    RotationStatus,
    SqlAlchemyAuthRepository,
)

TEST_DATABASE_URL = os.getenv("AUTH_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="AUTH_TEST_DATABASE_URL is not configured",
)


@pytest.fixture
async def migrated_database(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_DATABASE_URL", TEST_DATABASE_URL or "")
    config = Config("alembic.ini")
    await asyncio.to_thread(command.upgrade, config, "head")
    engine, session_factory = create_database(TEST_DATABASE_URL or "")
    try:
        yield session_factory
    finally:
        await engine.dispose()
        await asyncio.to_thread(command.downgrade, config, "base")


async def test_refresh_rotation_and_replay_are_transactional(migrated_database) -> None:
    session_factory = migrated_database
    user_id = uuid4()
    family_id = uuid4()
    old_hash = "a" * 64
    first_replacement = refresh_data(UUID(int=0), UUID(int=0), "b" * 64)
    second_replacement = refresh_data(UUID(int=0), UUID(int=0), "c" * 64)

    async with session_factory() as session:
        session.add(
            User(
                id=user_id,
                username="postgres-researcher",
                password_hash="not-used-by-repository-test",
                role=Role.RESEARCHER.value,
                is_active=True,
            )
        )
        await session.commit()
        await SqlAlchemyAuthRepository(session).create_refresh_session(
            refresh_data(user_id, family_id, old_hash)
        )

    async def rotate(replacement: RefreshSessionData):
        async with session_factory() as session:
            return await SqlAlchemyAuthRepository(session).rotate_refresh_session(
                old_hash, replacement
            )

    first_result, second_result = await asyncio.gather(
        rotate(first_replacement), rotate(second_replacement)
    )

    assert {first_result.status, second_result.status} == {
        RotationStatus.SUCCESS,
        RotationStatus.REUSED,
    }
    async with session_factory() as session:
        sessions = list(
            await session.scalars(
                select(RefreshSession).where(RefreshSession.family_id == family_id)
            )
        )
    assert len(sessions) == 2
    assert all(session.revoked_at is not None for session in sessions)


def refresh_data(user_id: UUID, family_id: UUID, token_hash: str) -> RefreshSessionData:
    return RefreshSessionData(
        id=uuid4(),
        user_id=user_id,
        family_id=family_id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(days=1),
        ip_address="127.0.0.1",
        user_agent="pytest",
    )
