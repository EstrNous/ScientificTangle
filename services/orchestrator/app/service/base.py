from uuid import UUID

import httpx

from shared.contracts import ApiError
from shared.web import INTERNAL_SERVICE_TOKEN_HEADER


class OrchestratorServiceError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        query_run_id: UUID | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.query_run_id = query_run_id
        super().__init__(message)


class BaseService:
    def __init__(self, client: httpx.AsyncClient, internal_service_token: str = "") -> None:
        self._client = client
        self._internal_service_token = internal_service_token

    async def _request_downstream(
        self,
        method: str,
        base_url: str,
        path: str,
        payload: dict,
        request_id: str,
        service_name: str,
        authorization: str | None = None,
        internal_auth: bool = False,
    ) -> dict | list:
        headers = {"X-Request-ID": request_id}
        if authorization is not None:
            headers["Authorization"] = authorization
        if internal_auth:
            headers[INTERNAL_SERVICE_TOKEN_HEADER] = self._internal_service_token
        try:
            response = await self._client.request(
                method,
                f"{base_url}{path}",
                json=payload,
                headers=headers,
            )
            if response.status_code >= 400:
                raise self._downstream_error(response, service_name)
            return response.json()
        except httpx.TimeoutException as error:
            raise OrchestratorServiceError(
                504, f"{service_name}_timeout", f"{service_name} request timed out"
            ) from error
        except httpx.HTTPError as error:
            raise OrchestratorServiceError(
                503, f"{service_name}_unavailable", f"{service_name} service is unavailable"
            ) from error
        except ValueError as error:
            raise OrchestratorServiceError(
                502, f"invalid_{service_name}_response", f"{service_name} returned invalid data"
            ) from error

    @staticmethod
    def _downstream_error(response: httpx.Response, service_name: str) -> OrchestratorServiceError:
        status_code = response.status_code if 400 <= response.status_code < 600 else 502
        try:
            payload = ApiError.model_validate(response.json())
            return OrchestratorServiceError(status_code, payload.code, payload.message)
        except (ValueError, TypeError):
            return OrchestratorServiceError(
                status_code,
                f"{service_name}_error",
                f"{service_name} service request failed",
            )

    async def _post_internal_notification_event(
        self,
        notification_url: str,
        payload: dict,
        request_id: str,
    ) -> None:
        if not notification_url:
            return
        try:
            await self._client.post(
                f"{notification_url.rstrip('/')}/internal/v1/events",
                json=payload,
                headers={
                    "X-Request-ID": request_id,
                    INTERNAL_SERVICE_TOKEN_HEADER: self._internal_service_token,
                },
            )
        except httpx.HTTPError:
            return

    async def _post_internal_notification_match(
        self,
        notification_url: str,
        payload: dict,
        request_id: str,
    ) -> None:
        if not notification_url:
            return
        try:
            await self._client.post(
                f"{notification_url.rstrip('/')}/internal/v1/match",
                json=payload,
                headers={
                    "X-Request-ID": request_id,
                    INTERNAL_SERVICE_TOKEN_HEADER: self._internal_service_token,
                },
            )
        except httpx.HTTPError:
            return
