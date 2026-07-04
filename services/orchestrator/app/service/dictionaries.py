import logging
from uuid import UUID
from typing import Any
import httpx

from shared.contracts import DictionaryMetadata, DictionaryValidationResult
from app.service.base import BaseService, OrchestratorServiceError

logger = logging.getLogger(__name__)

class DictionaryService(BaseService):
    def __init__(
        self,
        repository: Any,  # Обычно привязан к IngestionTaskRepository или кастомному DictionaryRepository
        client: httpx.AsyncClient,
        knowledge_url: str,
        ingestion_url: str
    ) -> None:
        super().__init__(client)
        self._repo = repository
        self._knowledge_url = knowledge_url
        self._ingestion_url = ingestion_url

    async def upload_dictionary(
        self, 
        name: str, 
        file_content: bytes, 
        user_id: UUID, 
        request_id: str,
        authorization: str | None = None
    ) -> DictionaryMetadata:
        """Загружает кастомный словарь терминов, отправляет его на валидацию и сохраняет метаданные."""
        logger.info(f"[{request_id}] Uploading new dictionary '{name}' by user {user_id}")
        
        # 1. Отправляем файл на проверку структуры в downstream-сервис онтологий
        validation_payload = {"raw_data": file_content.decode("utf-8", errors="ignore")}
        raw_result = await self._request_downstream(
            method="POST",
            base_url=self._knowledge_url,
            path="/v1/dictionaries/validate",
            payload=validation_payload,
            request_id=request_id,
            service_name="knowledge_dictionary_validator",
            authorization=authorization
        )
        
        result = DictionaryValidationResult.model_validate(raw_result)
        if not result.is_valid:
            raise OrchestratorServiceError(
                status_code=422,
                code="invalid_dictionary_format",
                message=f"Dictionary validation failed: {', '.join(result.errors)}"
            )

        # 2. Сохраняем метаданные валидного словаря в нашей локальной БД оркестратора
        dictionary_meta = await self._repo.save_dictionary_meta(
            name=name,
            owner_id=user_id,
            terms_count=result.terms_count,
            checksum=result.checksum
        )
        
        return dictionary_meta

    async def list_dictionaries(self, user_id: UUID) -> list[DictionaryMetadata]:
        """Возвращает список доступных словарей для текущего пользователя."""
        return await self._repo.get_dictionaries_by_owner(user_id)

    async def get_active_dictionary(self, user_id: UUID) -> DictionaryMetadata | None:
        """Получает текущий активный словарь, который применяется к пайплайнам RAG/Ingestion."""
        return await self._repo.get_active_dictionary_for_user(user_id)

    async def activate_dictionary(
        self, 
        dictionary_id: UUID, 
        user_id: UUID, 
        request_id: str,
        authorization: str | None = None
    ) -> DictionaryMetadata:
        """Переключает активный словарь пользователя и синхронизирует состояние с ретривалом."""
        dictionary = await self._repo.get_dictionary_by_id(dictionary_id)
        if not dictionary:
            raise OrchestratorServiceError(404, "dictionary_not_found", f"Dictionary {dictionary_id} not found")
            
        if dictionary.owner_id != user_id:
            raise OrchestratorServiceError(403, "forbidden", "You don't have access to this dictionary")

        # Активируем локально
        await self._repo.set_active_dictionary(user_id, dictionary_id)
        
        # Оповещаем downstream-сервисы, чтобы они перестроили кэш правил маппинга
        await self._request_downstream(
            method="POST",
            base_url=self._ingestion_url,
            path=f"/v1/dictionaries/{dictionary_id}/activate",
            payload={"checksum": dictionary.checksum},
            request_id=request_id,
            service_name="ingestion_dictionary_sync",
            authorization=authorization
        )
        
        return dictionary