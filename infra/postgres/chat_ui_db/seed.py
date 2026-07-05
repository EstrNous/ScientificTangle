import asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from .models import AdminSetting, ChatMessage, ChatSession, ServiceState
from .config import settings

async def seed_chat() -> None:
    engine = create_async_engine(str(settings.database_url))
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # Создаем демо-сессию
        s = ChatSession(id=uuid4(), user_id=uuid4(), title="Демо: Очистка воды")
        m = ChatMessage(session_id=s.id, role="user", content="Как обессолить воду?")
        settings_row = AdminSetting(
            setting_key="demo.locale",
            setting_value={"locale": "ru"},
            description="Демо настройка локали",
        )
        service_state = ServiceState(service_name="knowledge", status="healthy")
        session.add_all([s, m, settings_row, service_state])
        await session.commit()
        print("Chat UI DB seeded.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_chat())