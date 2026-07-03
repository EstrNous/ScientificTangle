import asyncio
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from .models import ExportJob
from .config import settings

async def seed_export() -> None:
    engine = create_async_engine(str(settings.database_url))
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        # Создаем пример завершенного экспорта
        job = ExportJob(
            id=uuid4(),
            user_id=uuid4(),
            status="completed",
            format="markdown",
            file_url="s3://exports/example_report.md"
        )
        session.add(job)
        await session.commit()
        print("Export DB seeded.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_export())