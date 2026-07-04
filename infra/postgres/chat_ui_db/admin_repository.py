from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import AdminSetting, ServiceState


class AdminSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_setting(self, setting_key: str) -> AdminSetting | None:
        return await self._session.scalar(
            select(AdminSetting).where(AdminSetting.setting_key == setting_key)
        )

    async def upsert_setting(
        self,
        setting_key: str,
        setting_value: dict,
        description: str | None = None,
    ) -> AdminSetting:
        existing = await self.get_setting(setting_key)
        if existing is None:
            setting = AdminSetting(
                setting_key=setting_key,
                setting_value=setting_value,
                description=description,
            )
            self._session.add(setting)
        else:
            existing.setting_value = setting_value
            if description is not None:
                existing.description = description
            setting = existing
        await self._session.commit()
        await self._session.refresh(setting)
        return setting


class ServiceStateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_state(self, service_name: str) -> ServiceState | None:
        return await self._session.scalar(
            select(ServiceState).where(ServiceState.service_name == service_name)
        )

    async def upsert_state(self, service_name: str, status: str) -> ServiceState:
        existing = await self.get_state(service_name)
        if existing is None:
            state = ServiceState(service_name=service_name, status=status)
            self._session.add(state)
        else:
            existing.status = status
            state = existing
        await self._session.commit()
        await self._session.refresh(state)
        return state
