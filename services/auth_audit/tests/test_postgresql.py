import asyncio
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import func, select

from infra.postgres.auth_audit_db import create_database
from infra.postgres.auth_audit_db import RefreshSession, Role, User
from infra.postgres.auth_audit_db import (
    IdentityConflictError,
    NewUserData,
    RefreshSessionData,
    RotationStatus,
    SqlAlchemyAuthRepository,
)
from app.service.security import PasswordManager

TEST_DATABASE_URL = os.getenv("AUTH_TEST_DATABASE_URL")
ALEMBIC_INI_PATH = Path(__file__).resolve().parents[1] / "alembic.ini"
pytestmark = pytest.mark.skipif(
    TEST_DATABASE_URL is None,
    reason="AUTH_TEST_DATABASE_URL is not configured",
)


@pytest.fixture
async def migrated_database(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_DATABASE_URL", TEST_DATABASE_URL or "")
    config = Config(str(ALEMBIC_INI_PATH))
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


async def test_concurrent_registration_enforces_unique_email(migrated_database) -> None:
    session_factory = migrated_database
    password_hash = PasswordManager().hash("Password1")

    async def create(username: str):
        async with session_factory() as session:
            return await SqlAlchemyAuthRepository(session).create_user(
                NewUserData(
                    username=username,
                    email="shared@example.com",
                    password_hash=password_hash,
                    role=Role.EXTERNAL_PARTNER,
                )
            )

    results = await asyncio.gather(
        create("first-user"), create("second-user"), return_exceptions=True
    )

    assert sum(isinstance(result, User) for result in results) == 1
    assert sum(isinstance(result, IdentityConflictError) for result in results) == 1
    async with session_factory() as session:
        count = await session.scalar(
            select(func.count()).select_from(User).where(User.email == "shared@example.com")
        )
    assert count == 1


async def test_password_change_revokes_all_postgresql_sessions(migrated_database) -> None:
    session_factory = migrated_database
    user_id = uuid4()
    family_id = uuid4()
    async with session_factory() as session:
        repository = SqlAlchemyAuthRepository(session)
        session.add(
            User(
                id=user_id,
                username="password-user",
                email="password-user@example.com",
                password_hash="old-hash",
                role=Role.RESEARCHER.value,
                is_active=True,
            )
        )
        await session.commit()
        await repository.create_refresh_session(refresh_data(user_id, family_id, "d" * 64))
        await repository.create_refresh_session(refresh_data(user_id, family_id, "e" * 64))
        changed = await repository.change_password(user_id, "new-hash")

    assert changed is not None
    assert changed.password_hash == "new-hash"
    async with session_factory() as session:
        sessions = list(
            await session.scalars(select(RefreshSession).where(RefreshSession.user_id == user_id))
        )
    assert len(sessions) == 2
    assert all(session.revoked_at is not None for session in sessions)
