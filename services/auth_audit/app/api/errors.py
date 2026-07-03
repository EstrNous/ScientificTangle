from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from infra.postgres.auth_audit_db import ErrorDetails, ErrorResponse


class UnauthorizedError(Exception):
    pass


class ForbiddenError(Exception):
    pass


class ConflictError(Exception):
    pass


class NotFoundError(Exception):
    pass


def error_response(request: Request, code: str, message: str, status_code: int) -> JSONResponse:
    request_id = getattr(request.state, "request_id", str(uuid4()))
    payload = ErrorResponse(error=ErrorDetails(code=code, message=message, request_id=request_id))
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else None
    return JSONResponse(status_code=status_code, content=payload.model_dump(), headers=headers)


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(UnauthorizedError)
    async def unauthorized_handler(request: Request, error: UnauthorizedError) -> JSONResponse:
        return error_response(request, "UNAUTHORIZED", "Authentication is required", 401)

    @app.exception_handler(ForbiddenError)
    async def forbidden_handler(request: Request, error: ForbiddenError) -> JSONResponse:
        return error_response(request, "FORBIDDEN", "Access is denied", 403)

    @app.exception_handler(ConflictError)
    async def conflict_handler(request: Request, error: ConflictError) -> JSONResponse:
        return error_response(request, "IDENTITY_ALREADY_EXISTS", "Identity already exists", 409)

    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, error: NotFoundError) -> JSONResponse:
        return error_response(request, "USER_NOT_FOUND", "User was not found", 404)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, error: RequestValidationError) -> JSONResponse:
        return error_response(request, "VALIDATION_ERROR", "Request validation failed", 422)

    @app.exception_handler(StarletteHTTPException)
    async def http_handler(request: Request, error: StarletteHTTPException) -> JSONResponse:
        return error_response(request, "HTTP_ERROR", "Request failed", error.status_code)

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, error: Exception) -> JSONResponse:
        return error_response(request, "INTERNAL_ERROR", "Internal server error", 500)
