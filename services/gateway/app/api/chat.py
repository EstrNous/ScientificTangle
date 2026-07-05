from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, status

from infra.postgres.chat_ui_db.schemas import ChatMessageCreate, ChatSessionCreate
from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, forwarded_auth, require_principal

from ..core.dependencies import get_chat_service
from ..service.chat_service import ChatService, ChatServiceError

router = APIRouter(prefix="/chat", tags=["chat"])


@router.get("/sessions")
async def list_sessions(
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> list[dict]:
    try:
        return await service.list_sessions(principal)
    except ChatServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: ChatSessionCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> dict:
    try:
        return await service.create_session(principal, payload.title)
    except ChatServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> None:
    try:
        await service.delete_session(principal, session_id)
    except ChatServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error


@router.get("/sessions/{session_id}/messages")
async def list_messages(
    session_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> list[dict]:
    try:
        return await service.list_messages(principal, session_id)
    except ChatServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error


@router.post("/sessions/{session_id}/messages")
async def send_message(
    session_id: UUID,
    payload: ChatMessageCreate,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[ChatService, Depends(get_chat_service)],
) -> dict:
    authorization, request_id = forwarded_auth()
    try:
        return await service.send_message(
            principal,
            session_id,
            payload.content,
            authorization,
            request_id,
            payload.query_run_id,
        )
    except ChatServiceError as error:
        raise ServiceError(error.status_code, error.code, error.message) from error
