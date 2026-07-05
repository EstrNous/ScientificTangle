import asyncio
import argparse
from uuid import uuid4
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from shared.contracts import IngestionTaskStatus, QueryRunStatus

from .models import IngestionTask, Permission, QueryRun, Role, RolePermission
from .config import settings


async def seed_orchestrator() -> None:
    # Используем URL из настроек сервиса
    engine = create_async_engine(str(settings.database_url))
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        roles = [
            Role(name="admin", description="Полный доступ"),
            Role(name="researcher", description="Исследователь"),
            Role(name="partner", description="Внешний партнёр"),
        ]
        permissions = [
            Permission(name="query.run", description="Запуск запросов"),
            Permission(name="ingestion.upload", description="Загрузка документов"),
            Permission(name="export.create", description="Экспорт отчётов"),
            Permission(name="admin.read", description="Просмотр админки"),
        ]
        role_permissions = [
            RolePermission(role_name="admin", permission_name="query.run"),
            RolePermission(role_name="admin", permission_name="ingestion.upload"),
            RolePermission(role_name="admin", permission_name="export.create"),
            RolePermission(role_name="admin", permission_name="admin.read"),
            RolePermission(role_name="researcher", permission_name="query.run"),
            RolePermission(role_name="researcher", permission_name="ingestion.upload"),
            RolePermission(role_name="researcher", permission_name="export.create"),
            RolePermission(role_name="partner", permission_name="query.run"),
        ]
        session.add_all(roles + permissions + role_permissions)
        tasks = [
            IngestionTask(id=uuid4(), user_id=uuid4(), status=IngestionTaskStatus.COMPLETED.value),
            IngestionTask(id=uuid4(), user_id=uuid4(), status=IngestionTaskStatus.PROCESSING.value),
        ]

        # Создаем тестовые QueryRun
        runs = [
            QueryRun(
                id=uuid4(),
                user_id=uuid4(),
                status=QueryRunStatus.COMPLETED.value,
                raw_question="Какие методы обессоливания применимы?",
                request_id="seed",
                query_ir={"goal": "desalination", "materials": ["sulfates"]},
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
