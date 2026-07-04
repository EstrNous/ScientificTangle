import httpx
import uuid
from typing import Any, List
from fastapi import UploadFile, BackgroundTasks
from app.core.config import settings
from app.models.ingestion import IngestionTask, IngestionStatus
from app.models.auth import AuthenticatedPrincipal
from app.service.base import BaseService, OrchestratorServiceError

class IngestionService(BaseService):
    def __init__(self, client: httpx.AsyncClient):
        super().__init__(client)
        self._ingestion_url = f"{settings.INGESTION_SERVICE_URL}/v1/parse"
        self._db_tasks_mock: dict[str, IngestionTask] = {}

    async def start_ingestion_task(
        self, 
        files: List[UploadFile], 
        principal: AuthenticatedPrincipal, 
        request_id: str,
        background_tasks: BackgroundTasks
    ) -> IngestionTask:
        """
        Инициализирует задачу инжеста и безопасно ставит её в BackgroundTasks от FastAPI.
        """
        task_id = str(uuid.uuid4())
        
        task = IngestionTask(
            id=task_id,
            status=IngestionStatus.PROCESSING,
            user_id=principal.user_id,
            files_count=len(files)
        )
        self._db_tasks_mock[task_id] = task

        # Вычитываем байты до ухода в фон, пока жив поток запроса FastAPI
        prepared_files = []
        for f in files:
            content = await f.read()
            prepared_files.append((f.filename, content, f.content_type))

        background_tasks.add_task(
            self._run_ingestion_pipeline,
            task_id=task.id,
            files=prepared_files,
            request_id=request_id,
            token=principal.token
        )
        
        return task

    async def get_task_status(self, task_id: str, principal: AuthenticatedPrincipal) -> IngestionTask:
        task = self._db_tasks_mock.get(task_id)
        if not task:
            raise OrchestratorServiceError("Task not found", status_code=404)
        if task.user_id != principal.user_id:
            raise OrchestratorServiceError("Access denied", status_code=403)
        return task

    async def _run_ingestion_pipeline(
        self, 
        task_id: str, 
        files: List[tuple[str, bytes, str]], 
        request_id: str, 
        token: str
    ) -> None:
        """
        Фоновый пайплайн обработки, отправляющий бинарники через multipart/form-data.
        """
        headers = self._build_headers(request_id, token)
        
        # Формируем корректную multipart структуру для httpx
        httpx_files = [
            ("files", (filename, content, content_type))
            for filename, content, content_type in files
        ]

        try:
            response = await self._client.post(
                self._ingestion_url,
                files=httpx_files,
                headers=headers,
                timeout=300.0
            )
            
            task = self._db_tasks_mock.get(task_id)
            if not task:
                return

            if response.status_code == 200:
                task.status = IngestionStatus.COMPLETED
                task.result_metadata = response.json()
            else:
                task.status = IngestionStatus.FAILED
                task.error_message = f"Ingestion downstream service returned {response.status_code}"
                
        except Exception as e:
            task = self._db_tasks_mock.get(task_id)
            if task:
                task.status = IngestionStatus.FAILED
                task.error_message = str(e)