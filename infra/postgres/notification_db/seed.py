import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from config import settings
from models import Notification, UserInterest

DEMO_USERNAME = "researcher"

DEMO_NOTIFICATIONS = (
    {
        "type": "interest_match",
        "message": "Совпадение с подпиской: никель, католит",
        "reference_id": "nickel_report.pdf",
        "is_read": False,
        "created_at": datetime.now(UTC) - timedelta(hours=2),
    },
    {
        "type": "ingestion_complete",
        "message": "Извлечено 24 сущности, 3 новых для графа знаний",
        "reference_id": "hydromet_2024.pdf",
        "is_read": False,
        "created_at": datetime.now(UTC) - timedelta(days=1),
    },
    {
        "type": "conflict_detected",
        "message": "Источники A и B дают разные диапазоны pH католита: 4.2–4.8 и 5.0–5.4",
        "reference_id": None,
        "is_read": False,
        "created_at": datetime.now(UTC) - timedelta(days=1, hours=6),
    },
    {
        "type": "interest_match",
        "message": "Совпадение с подпиской: очистка воды, сорбция",
        "reference_id": "water_treatment_review.pdf",
        "is_read": True,
        "created_at": datetime.now(UTC) - timedelta(days=2),
    },
)


async def resolve_user_id(session, username: str) -> UUID:
    result = await session.execute(
        text("SELECT id FROM users WHERE username = :username LIMIT 1"),
        {"username": username},
    )
    row = result.first()
    if row is None:
        raise RuntimeError(f"user '{username}' not found; run auth-seed-users first")
    return row[0]


async def seed_notifications(username: str = DEMO_USERNAME) -> None:
    engine = create_async_engine(str(settings.database_url))
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        user_id = await resolve_user_id(session, username)
        existing = await session.scalars(
            select(Notification.id).where(Notification.user_id == user_id).limit(1)
        )
        if existing.first() is not None:
            print(f"Notifications for '{username}' already exist, skip seed.")
            await engine.dispose()
            return

        interest = await session.scalar(select(UserInterest).where(UserInterest.user_id == user_id))
        if interest is None:
            session.add(
                UserInterest(
                    user_id=user_id,
                    raw_text="Интересуюсь процессами электроэкстракции и очистки воды",
                    extracted_entities={"topics": ["электроэкстракция", "очистка воды", "никель"]},
                )
            )

        for item in DEMO_NOTIFICATIONS:
            session.add(Notification(user_id=user_id, **item))

        await session.commit()
        print(f"Notification DB seeded for '{username}'.")

    await engine.dispose()


def main() -> None:
    asyncio.run(seed_notifications())


if __name__ == "__main__":
    main()
