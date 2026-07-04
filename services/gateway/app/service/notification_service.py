from datetime import datetime
from uuid import UUID

import httpx

from shared.contracts import (
    ApiError,
    NotificationListPayload,
    NotificationMarkReadPayload,
    UserInterestsPayload,
    UserInterestsUpdatePayload,
)
from shared.security import AuthenticatedPrincipal
from shared.web import INTERNAL_SERVICE_TOKEN_HEADER

from ..core.config import settings


class NotificationServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class NotificationService:
    def __init__(
        self,
        client: httpx.AsyncClient,
        notification_url: str | None = None,
        internal_service_token: str | None = None,
    ) -> None:
        self._client = client
        self._notification_url = (notification_url or settings.notification_url).rstrip("/")
        self._internal_service_token = (
            internal_service_token
            if internal_service_token is not None
            else settings.internal_service_token
        )

    async def list_notifications(
        self,
        principal: AuthenticatedPrincipal,
        since: datetime | None,
        authorization: str,
        request_id: str,
    ) -> NotificationListPayload:
        params: dict[str, str] = {}
        if since is not None:
            params["since"] = since.isoformat()
        response = await self._request(
            "GET",
            "/notifications",
            authorization,
            request_id,
            params=params or None,
        )
        return NotificationListPayload.model_validate(response.json())

    async def mark_read(
        self,
        principal: AuthenticatedPrincipal,
        notification_id: UUID,
        authorization: str,
        request_id: str,
    ) -> NotificationMarkReadPayload:
        response = await self._request(
            "POST",
            f"/notifications/{notification_id}/read",
            authorization,
            request_id,
        )
        return NotificationMarkReadPayload.model_validate(response.json())

    async def mark_all_read(
        self,
        principal: AuthenticatedPrincipal,
        authorization: str,
        request_id: str,
    ) -> NotificationMarkReadPayload:
        response = await self._request(
            "POST",
            "/notifications/read-all",
            authorization,
            request_id,
        )
        return NotificationMarkReadPayload.model_validate(response.json())

    async def get_interests(
        self,
        principal: AuthenticatedPrincipal,
        authorization: str,
        request_id: str,
    ) -> UserInterestsPayload:
        response = await self._request("GET", "/interests", authorization, request_id)
        return UserInterestsPayload.model_validate(response.json())

    async def update_interests(
        self,
        principal: AuthenticatedPrincipal,
        payload: UserInterestsUpdatePayload,
        authorization: str,
        request_id: str,
    ) -> UserInterestsPayload:
        response = await self._request(
            "PUT",
            "/interests",
            authorization,
            request_id,
            json_body=payload.model_dump(mode="json"),
        )
        return UserInterestsPayload.model_validate(response.json())

    async def create_conflict_event(
        self,
        user_id: UUID,
        event_type: str,
        message: str,
        reference_id: str | None,
        reference_type: str | None,
        match_score: float | None,
        match_reason: str,
        match_payload: dict | None,
        request_id: str,
    ) -> None:
        try:
            await self._client.post(
                f"{self._notification_url}/internal/v1/events",
                json={
                    "user_id": str(user_id),
                    "type": event_type,
                    "message": message,
                    "reference_id": reference_id,
                    "reference_type": reference_type,
                    "match_score": match_score,
                    "match_reason": match_reason,
                    "match_payload": match_payload,
                },
                headers={
                    "X-Request-ID": request_id,
                    INTERNAL_SERVICE_TOKEN_HEADER: self._internal_service_token,
                },
            )
        except httpx.HTTPError:
            return

    async def _request(
        self,
        method: str,
        path: str,
        authorization: str,
        request_id: str,
        json_body: dict | None = None,
        params: dict[str, str] | None = None,
    ) -> httpx.Response:
        try:
            response = await self._client.request(
                method,
                f"{self._notification_url}{path}",
                json=json_body,
                params=params,
                headers={"Authorization": authorization, "X-Request-ID": request_id},
            )
        except httpx.TimeoutException as error:
            raise NotificationServiceError(504, "notification_timeout", "Notification request timed out") from error
        except httpx.HTTPError as error:
            raise NotificationServiceError(503, "notification_unavailable", "Notification service is unavailable") from error
        if response.status_code >= 400:
            raise self._downstream_error(response)
        return response

    @staticmethod
    def _downstream_error(response: httpx.Response) -> NotificationServiceError:
        status_code = response.status_code if 400 <= response.status_code < 600 else 502
        try:
            payload = ApiError.model_validate(response.json())
            return NotificationServiceError(status_code, payload.code, payload.message)
        except (ValueError, TypeError):
            return NotificationServiceError(
                status_code, "downstream_error", "Notification service request failed"
            )
