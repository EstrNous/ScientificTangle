import argparse
import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from .config import settings
from .e2_fixtures import seed_e2_fixtures


async def main() -> None:
    engine = create_async_engine(str(settings.database_url))
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        counts = await seed_e2_fixtures(session)
        print(f"E2 fixtures seeded: {counts}")
    await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed E2 review/source/delete fixtures")
    parser.parse_args()
    asyncio.run(main())
