import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from shared.contracts import ApiError
from shared.utils import generate_request_id


class ServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ServiceError, _service_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(HTTPException, _http_error)
    app.add_exception_handler(Exception, _unexpected_error)


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", generate_request_id())


def _response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    payload = ApiError(code=code, message=message, request_id=_request_id(request))
    return JSONResponse(status_code=status_code, content=payload.model_dump(mode="json"))


async def _service_error(request: Request, error: ServiceError) -> JSONResponse:
    return _response(request, error.status_code, error.code, error.message)


async def _validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
    return _response(request, 422, "validation_error", "Request validation failed")


async def _http_error(request: Request, error: HTTPException) -> JSONResponse:
    message = error.detail if isinstance(error.detail, str) else "Request failed"
    return _response(request, error.status_code, "http_error", message)


async def _unexpected_error(request: Request, error: Exception) -> JSONResponse:
    structlog.get_logger().exception(
        "unhandled_request_error",
        request_id=_request_id(request),
        path=request.url.path,
        error=str(error),
    )
    return _response(request, 500, "internal_error", "Internal server error")
