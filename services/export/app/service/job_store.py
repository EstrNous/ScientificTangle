import json
from datetime import UTC, datetime
from uuid import UUID

from ..schemas import ExportArtifactMeta, ExportJobStatusResponse

try:
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:
    Redis = None
    RedisError = Exception


class JobStore:
    def __init__(self, redis_url: str, ttl_seconds: int = 30 * 24 * 3600) -> None:
        self._ttl_seconds = ttl_seconds
        self._memory: dict[str, str] = {}
        self._redis = self._connect(redis_url)

    async def save(self, job: ExportJobStatusResponse) -> None:
        payload = job.model_dump(mode="json")
        key = self._key(job.job_id)
        encoded = json.dumps(payload, ensure_ascii=False)
        if self._redis is not None:
            try:
                self._redis.setex(key, self._ttl_seconds, encoded)
                return
            except RedisError:
                pass
        self._memory[key] = encoded

    async def get(self, job_id: UUID) -> ExportJobStatusResponse | None:
        key = self._key(job_id)
        encoded: str | None = None
        if self._redis is not None:
            try:
                raw = self._redis.get(key)
                if raw is not None:
                    encoded = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
            except RedisError:
                encoded = None
        if encoded is None:
            encoded = self._memory.get(key)
        if encoded is None:
            return None
        return ExportJobStatusResponse.model_validate(json.loads(encoded))

    async def create_pending(
        self,
        job_id: UUID,
        user_id: UUID,
        query_run_id: UUID,
        export_format: str,
    ) -> ExportJobStatusResponse:
        job = ExportJobStatusResponse(
            job_id=job_id,
            user_id=user_id,
            query_run_id=query_run_id,
            format=export_format,
            status="pending",
            created_at=datetime.now(UTC),
        )
        await self.save(job)
        return job

    async def mark_processing(self, job_id: UUID) -> ExportJobStatusResponse | None:
        job = await self.get(job_id)
        if job is None:
            return None
        updated = job.model_copy(update={"status": "processing"})
        await self.save(updated)
        return updated

    async def mark_completed(
        self,
        job_id: UUID,
        artifacts: list[ExportArtifactMeta],
    ) -> ExportJobStatusResponse | None:
        job = await self.get(job_id)
        if job is None:
            return None
        updated = job.model_copy(
            update={
                "status": "completed",
                "artifacts": artifacts,
                "completed_at": datetime.now(UTC),
                "error_message": None,
            }
        )
        await self.save(updated)
        return updated

    async def mark_failed(self, job_id: UUID, message: str) -> ExportJobStatusResponse | None:
        job = await self.get(job_id)
        if job is None:
            return None
        updated = job.model_copy(
            update={
                "status": "failed",
                "error_message": message,
                "completed_at": datetime.now(UTC),
            }
        )
        await self.save(updated)
        return updated

    @staticmethod
    def _key(job_id: UUID) -> str:
        return f"export:job:{job_id}"

    @staticmethod
    def _connect(redis_url: str):
        if Redis is None:
            return None
        try:
            client = Redis.from_url(redis_url, decode_responses=False)
            client.ping()
            return client
        except Exception:
            return None
