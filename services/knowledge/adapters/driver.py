from __future__ import annotations

from neo4j import AsyncDriver, AsyncGraphDatabase


def create_driver(uri: str, user: str, password: str) -> AsyncDriver:
    return AsyncGraphDatabase.driver(uri, auth=(user, password))


async def verify_connectivity(driver: AsyncDriver) -> bool:
    try:
        await driver.verify_connectivity()
        return True
    except Exception:
        return False
