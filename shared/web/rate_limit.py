from __future__ import annotations

import hashlib
import time
from asyncio import Lock
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

try:
    from redis.asyncio import Redis
    from redis.exceptions import RedisError
except ModuleNotFoundError:
    Redis = None
    RedisError = Exception

from shared.contracts import ApiError
from shared.utils import generate_request_id


@dataclass(frozen=True, slots=True)
class RateLimitRule:
    name: str
    limit: int
    window_seconds: int = 60
    path_prefixes: tuple[str, ...] = ()
    methods: tuple[str, ...] = ()

    def matches(self, request: Request) -> bool:
        if self.methods and request.method.upper() not in self.methods:
            return False
        if not self.path_prefixes:
            return True
        return any(request.url.path.startswith(prefix) for prefix in self.path_prefixes)


class LocalRateLimitStore:
    def __init__(self) -> None:
        self._buckets: dict[str, tuple[float, int]] = {}
        self._lock = Lock()

    async def increment(self, key: str, window_seconds: int) -> int:
        async with self._lock:
            now = time.monotonic()
            expires_at, count = self._buckets.get(key, (0.0, 0))
            if expires_at <= now:
                expires_at = now + window_seconds
                count = 0
            count += 1
            self._buckets[key] = (expires_at, count)
            return count


class RedisRateLimitStore:
    def __init__(self, redis_url: str, key_prefix: str) -> None:
        if Redis is None:
            raise RedisError("redis package is not installed")
        self._redis = Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=0.2,
            socket_timeout=0.2,
        )
        self._key_prefix = key_prefix

    async def increment(self, key: str, window_seconds: int) -> int:
        namespaced = f"{self._key_prefix}:{key}"
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.incr(namespaced)
            pipe.expire(namespaced, window_seconds, nx=True)
            result = await pipe.execute()
        return int(result[0])

    async def aclose(self) -> None:
        await self._redis.aclose()


class RateLimiter:
    def __init__(
        self,
        redis_url: str,
        key_prefix: str,
        use_redis: bool = True,
    ) -> None:
        self._redis = RedisRateLimitStore(redis_url, key_prefix) if use_redis and Redis is not None else None
        self._local = LocalRateLimitStore()
        self._logger = structlog.get_logger()

    async def increment(self, key: str, window_seconds: int) -> int:
        if self._redis is None:
            return await self._local.increment(key, window_seconds)
        try:
            return await self._redis.increment(key, window_seconds)
        except RedisError as error:
            self._logger.warning("rate_limit_redis_degraded", error=str(error))
            return await self._local.increment(key, window_seconds)

    async def aclose(self) -> None:
        if self._redis is not None:
            await self._redis.aclose()


def install_rate_limit_middleware(
    app: FastAPI,
    *,
    enabled: bool,
    redis_url: str,
    service_name: str,
    rules: tuple[RateLimitRule, ...],
    excluded_paths: tuple[str, ...] = (),
    trust_proxy_headers: bool = False,
    use_redis: bool = True,
) -> RateLimiter | None:
    if not enabled:
        return None

    limiter = RateLimiter(
        redis_url=redis_url,
        key_prefix=f"rate_limit:{service_name}",
        use_redis=use_redis,
    )
    app.state.rate_limiter = limiter

    @app.middleware("http")
    async def rate_limit_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        if _is_excluded(request, excluded_paths):
            return await call_next(request)
        rule = _match_rule(request, rules)
        if rule is None:
            return await call_next(request)
        client_key = _client_key(request, trust_proxy_headers)
        key = _bucket_key(rule, client_key)
        count = await limiter.increment(key, rule.window_seconds)
        if count <= rule.limit:
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(rule.limit)
            response.headers["X-RateLimit-Remaining"] = str(rule.limit - count)
            return response
        return _rate_limited_response(request, rule)

    return limiter


def _is_excluded(request: Request, excluded_paths: tuple[str, ...]) -> bool:
    if request.method.upper() == "OPTIONS":
        return True
    return request.url.path in excluded_paths


def _match_rule(request: Request, rules: tuple[RateLimitRule, ...]) -> RateLimitRule | None:
    return next((rule for rule in rules if rule.matches(request)), None)


def _client_key(request: Request, trust_proxy_headers: bool) -> str:
    if trust_proxy_headers:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",", maxsplit=1)[0].strip()
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip.strip()
    if request.client is None:
        return "unknown"
    return request.client.host


def _bucket_key(rule: RateLimitRule, client_key: str) -> str:
    raw = f"{rule.name}:{client_key}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _rate_limited_response(request: Request, rule: RateLimitRule) -> JSONResponse:
    request_id = getattr(request.state, "request_id", generate_request_id())
    payload = ApiError(
        code="rate_limited",
        message="Too many requests",
        request_id=request_id,
    )
    return JSONResponse(
        status_code=429,
        content=payload.model_dump(mode="json", exclude_none=True),
        headers={
            "Retry-After": str(rule.window_seconds),
            "X-RateLimit-Limit": str(rule.limit),
            "X-RateLimit-Remaining": "0",
        },
    )
