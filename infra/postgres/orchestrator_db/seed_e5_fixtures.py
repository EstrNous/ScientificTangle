import argparse
import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .config import settings
from .e5_fixtures import seed_e5_fixtures


async def main() -> None:
    engine = create_async_engine(str(settings.database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        counts = await seed_e5_fixtures(session)
        print(f"E5 product events fixtures seeded: {counts}")
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed E5 export/audit/notification fixtures")
    parser.parse_args()
    asyncio.run(main())
