from fastapi import Request

from app.service.service import IngestionService


def get_ingestion_service(request: Request) -> IngestionService:
    return request.app.state.ingestion_service
