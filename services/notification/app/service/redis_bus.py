import json
from typing import Any

import structlog

from shared.contracts import NotificationPayload

logger = structlog.get_logger()


class NotificationRedisBus:
    def __init__(
        self,
        redis_url: str,
        *,
        enabled: bool,
        delivery_channel: str,
        created_channel: str,
    ) -> None:
        self._redis_url = redis_url
        self._enabled = enabled
        self._delivery_channel = delivery_channel
        self._created_channel = created_channel
        self._redis = None
        self._available = False
        if enabled:
            self._connect()

    @property
    def available(self) -> bool:
        return self._available

    @property
    def delivery_channel(self) -> str:
        return self._delivery_channel

    @property
    def redis_client(self):
        return self._redis

    def _connect(self) -> None:
        try:
            from redis.asyncio import Redis
            from redis.exceptions import RedisError
        except ImportError:
            logger.warning("notification_redis_package_missing")
            return
        try:
            client = Redis.from_url(self._redis_url, decode_responses=True)
        except RedisError as error:
            logger.warning("notification_redis_connect_failed", error=str(error))
            return
        self._redis = client
        self._available = True

    async def close(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None
        self._available = False

    async def publish_created(self, payload: NotificationPayload, request_id: str = "") -> None:
        if not self._available or self._redis is None:
            return
        message = {
            "request_id": request_id,
            "notification": payload.model_dump(mode="json"),
        }
        await self._publish(self._created_channel, message)

    async def publish_delivery(self, kind: str, payload: dict[str, Any], request_id: str = "") -> bool:
        if not self._available or self._redis is None:
            return False
        message = {
            "kind": kind,
            "request_id": request_id,
            "payload": payload,
        }
        await self._publish(self._delivery_channel, message)
        return True

    async def _publish(self, channel: str, payload: dict[str, Any]) -> None:
        try:
            from redis.exceptions import RedisError
        except ImportError:
            return
        try:
            await self._redis.publish(channel, json.dumps(payload, ensure_ascii=False))
        except RedisError as error:
            logger.warning("notification_redis_publish_failed", channel=channel, error=str(error))
