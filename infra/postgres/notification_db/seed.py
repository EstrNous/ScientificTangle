import asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from .models import Notification, UserInterest
from .config import settings

async def seed_notifications() -> None:
    engine = create_async_engine(str(settings.database_url))
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # Тестовое уведомление
        note = Notification(
            id=uuid4(),
            user_id=uuid4(),
            type="info",
            message="Найден новый документ по теме: 'Гидрометаллургия никеля'"
        )
        # Тестовый профиль интересов
        interest = UserInterest(
            id=uuid4(),
            user_id=note.user_id,
            raw_text="Интересуюсь процессами электроэкстракции и очистки воды",
            extracted_entities={"topics": ["электроэкстракция", "очистка воды"]}
        )
        session.add_all([note, interest])
        await session.commit()
        print("Notification DB seeded.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_notifications())