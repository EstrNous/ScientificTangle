import httpx
from uuid import UUID
from shared.contracts import ApiError

class OrchestratorServiceError(Exception):
    """Кастомное исключение для красивого перехвата ошибок микросервисов в FastAPI."""
    def __init__(self, status_code: int, code: str, message: str, query_run_id: UUID | None = None) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.query_run_id = query_run_id
        super().__init__(message)

class BaseService:
    def __init__(self, client: httpx.AsyncClient) -> None:
        # Все дочерние сервисы получат эту переменную автоматически
        self._client = client

    async def _request_downstream(
        self, method: str, base_url: str, path: str, payload: dict, request_id: str, service_name: str, authorization: str | None = None
    ) -> dict | list:
        """
        Централизованный метод для отправки HTTP-запросов к соседним микросервисам.
        Сам подставит X-Request-ID, сам обработает таймауты и упавшие сервисы.
        """
        headers = {"X-Request-ID": request_id}
        if authorization:
            headers["Authorization"] = authorization
        try:
            response = await self._client.request(method, f"{base_url.rstrip('/')}{path}", json=payload, headers=headers)
            if response.status_code >= 400:
                raise self._downstream_error(response, service_name)
            return response.json()
        except httpx.TimeoutException as error:
            # Если условный сервис парсинга документов завис, мы отдаем внятный 504 статус
            raise OrchestratorServiceError(504, f"{service_name}_timeout", f"{service_name} request timed out") from error
        except httpx.HTTPError as error:
            # Если микросервис вообще лежит
            raise OrchestratorServiceError(503, f"{service_name}_unavailable", f"{service_name} service is unavailable") from error
        except ValueError as error:
            # Если микросервис вместо JSON вернул 500-ю HTML-страницу от nginx
            raise OrchestratorServiceError(502, f"invalid_{service_name}_response", f"{service_name} returned invalid data") from error

    def _downstream_error(self, response: httpx.Response, service_name: str) -> OrchestratorServiceError:
        """Парсит ошибку, прилетевшую от микросервиса, приводя её к нашему стандарту API."""
        status_code = response.status_code if 400 <= response.status_code < 600 else 502
        try:
            payload = ApiError.model_validate(response.json())
            return OrchestratorServiceError(status_code, payload.code, payload.message)
        except (ValueError, TypeError):
            return OrchestratorServiceError(status_code, f"{service_name}_error", f"{service_name} service request failed")