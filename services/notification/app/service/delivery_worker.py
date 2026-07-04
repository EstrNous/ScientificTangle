import asyncio
import json

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from ..core.config import Settings
from .delivery_handler import NotificationDeliveryHandler
from .redis_bus import NotificationRedisBus

logger = structlog.get_logger()


class NotificationDeliveryWorker:
    def __init__(
        self,
        redis_bus: NotificationRedisBus,
        session_factory: async_sessionmaker[AsyncSession],
        http_client: httpx.AsyncClient | None,
        resolved_settings: Settings,
        *,
        publish_created: bool = True,
        retry_seconds: int = 5,
    ) -> None:
        self._redis_bus = redis_bus
        self._handler = NotificationDeliveryHandler(session_factory, http_client, resolved_settings)
        self._publish_created = publish_created
        self._retry_seconds = retry_seconds
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._running = False

    @property
    def running(self) -> bool:
        return self._running

    def start(self) -> None:
        if not self._redis_bus.available or self._task is not None:
            return
        self._running = True
        self._task = asyncio.create_task(self._run(), name="notification-delivery-worker")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is not None:
            await self._task
            self._task = None
        self._running = False

    async def _run(self) -> None:
        try:
            while not self._stop.is_set():
                try:
                    await self._listen()
                except asyncio.CancelledError:
                    break
                except Exception as error:
                    logger.warning("notification_delivery_worker_restarting", error=str(error))
                    await asyncio.sleep(self._retry_seconds)
        finally:
            self._running = False

    async def _listen(self) -> None:
        redis_client = self._redis_bus.redis_client
        if redis_client is None:
            await asyncio.sleep(5)
            return
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(self._redis_bus.delivery_channel)
        logger.info(
            "notification_delivery_worker_started",
            channel=self._redis_bus.delivery_channel,
        )
        try:
            async for message in pubsub.listen():
                if self._stop.is_set():
                    break
                if message.get("type") != "message":
                    continue
                data = message.get("data")
                if not isinstance(data, str):
                    continue
                await self._process_message(data)
        finally:
            await pubsub.unsubscribe(self._redis_bus.delivery_channel)
            await pubsub.aclose()

    async def _process_message(self, raw_message: str) -> None:
        try:
            envelope = json.loads(raw_message)
        except ValueError:
            logger.warning("notification_delivery_invalid_json")
            return
        request_id = str(envelope.get("request_id") or "") if isinstance(envelope, dict) else ""
        try:
            created = await self._handler.handle_message(raw_message)
        except Exception as error:
            logger.warning(
                "notification_delivery_failed",
                request_id=request_id,
                error=str(error),
            )
            return
        if not self._publish_created:
            return
        for item in created:
            await self._redis_bus.publish_created(item, request_id=request_id)
