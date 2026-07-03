import asyncio
import argparse
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from .models import IngestionStatus, IngestionTask, QueryRun, QueryRunStatus
from .config import settings


async def seed_orchestrator() -> None:
    # Используем URL из настроек сервиса
    engine = create_async_engine(str(settings.database_url))
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # Создаем тестовые задачи Ingestion
        tasks = [
            IngestionTask(id=uuid4(), user_id=uuid4(), status=IngestionStatus.COMPLETED.value),
            IngestionTask(id=uuid4(), user_id=uuid4(), status=IngestionStatus.PROCESSING.value),
        ]

        # Создаем тестовые QueryRun
        runs = [
            QueryRun(
                id=uuid4(),
                user_id=uuid4(),
                status=QueryRunStatus.COMPLETED.value,
                query_ir={"goal": "desalination", "materials": ["sulfates"]}
            ),
        ]

        session.add_all(tasks + runs)
        await session.commit()
        print("Orchestrator DB seeded successfully.")

    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed orchestrator DB")
    parser.parse_args()
    asyncio.run(seed_orchestrator())