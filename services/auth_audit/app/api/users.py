from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from infra.postgres.auth_audit_db import (
    AdminUserUpdateRequest,
    Role,
    User,
    UserListResponse,
    UserResponse,
)
from shared.web import ServiceError

from ..core.dependencies import get_auth_service, get_request_context, require_roles
from ..service.service import AuthService, RequestContext, UserNotFoundError
from .auth import validate_origin

router = APIRouter()

AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
RequestContextDependency = Annotated[RequestContext, Depends(get_request_context)]
AdminUserDependency = Annotated[User, Depends(require_roles(Role.ADMIN))]


@router.get("/api/auth/users", response_model=UserListResponse)
async def list_users(
    admin: AdminUserDependency,
    service: AuthServiceDependency,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> UserListResponse:
    users, total = await service.list_users(offset, limit)
    return UserListResponse(
        items=[UserResponse.model_validate(user) for user in users],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.patch("/api/auth/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    payload: AdminUserUpdateRequest,
    request: Request,
    admin: AdminUserDependency,
    service: AuthServiceDependency,
    context: RequestContextDependency,
) -> UserResponse:
    validate_origin(request)
    try:
        updated = await service.update_user(
            user_id, payload.role, payload.is_active, admin, context
        )
    except UserNotFoundError as error:
        raise ServiceError(404, "user_not_found", "User was not found") from error
    return UserResponse.model_validate(updated)
