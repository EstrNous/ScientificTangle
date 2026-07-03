import argparse
import asyncio
import os
from dataclasses import dataclass

from sqlalchemy.dialects.postgresql import insert

from app.config import Settings
from app.database import create_database
from app.models import Role, User
from app.security import PasswordManager


@dataclass(frozen=True, slots=True)
class SeedUser:
    username: str
    password: str
    role: Role
    email: str | None


def load_seed_users() -> list[SeedUser]:
    users: list[SeedUser] = []
    for role in Role:
        prefix = f"AUTH_SEED_{role.value.upper()}"
        username = os.getenv(f"{prefix}_USERNAME")
        password = os.getenv(f"{prefix}_PASSWORD")
        email = os.getenv(f"{prefix}_EMAIL")
        if username is None and password is None:
            continue
        if not username or not password:
            raise ValueError(f"{prefix}_USERNAME and {prefix}_PASSWORD must be set together")
        users.append(
            SeedUser(
                username=username.strip().casefold(),
                password=password,
                role=role,
                email=email.strip().casefold() if email else None,
            )
        )
    if not users:
        raise ValueError("No seed users are configured")
    return users


async def seed_users() -> None:
    settings = Settings()
    engine, session_factory = create_database(settings.database_url)
    password_manager = PasswordManager()
    try:
        async with session_factory() as session:
            for seed_user in load_seed_users():
                statement = insert(User).values(
                    username=seed_user.username,
                    email=seed_user.email,
                    password_hash=password_manager.hash(seed_user.password),
                    role=seed_user.role.value,
                    is_active=True,
                )
                statement = statement.on_conflict_do_update(
                    index_elements=[User.username],
                    set_={
                        "email": statement.excluded.email,
                        "password_hash": statement.excluded.password_hash,
                        "role": statement.excluded.role,
                        "is_active": True,
                        "deactivated_at": None,
                    },
                )
                await session.execute(statement)
            await session.commit()
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(prog="auth-seed-users")
    parser.parse_args()
    asyncio.run(seed_users())


if __name__ == "__main__":
    main()
