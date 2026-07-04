from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from shared.security import AuthenticatedPrincipal
from shared.web import ServiceError, require_internal_service, require_principal

from ..schemas import ExportJobCreateRequest, ExportJobProcessResponse, ExportJobStatusResponse
from ..service.service import ExportService, ExportServiceError

router = APIRouter(prefix="/v1/jobs", tags=["export"])


def raise_service_error(error: ExportServiceError) -> None:
    raise ServiceError(error.status_code, error.code, error.message) from error


def get_export_service(request: Request) -> ExportService:
    return request.app.state.export_service


@router.post("", response_model=ExportJobProcessResponse, status_code=201)
async def create_job(
    request: Request,
    payload: ExportJobCreateRequest,
    service: Annotated[ExportService, Depends(get_export_service)],
    _: Annotated[None, Depends(require_internal_service)],
) -> ExportJobProcessResponse:
    try:
        return await service.create_job(payload, request.state.request_id)
    except ExportServiceError as error:
        raise_service_error(error)


@router.get("/{job_id}", response_model=ExportJobStatusResponse)
async def get_job_status(
    job_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[ExportService, Depends(get_export_service)],
) -> ExportJobStatusResponse:
    try:
        job = await service.get_job(job_id)
        if principal.role.value != "admin" and job.user_id != principal.user_id:
            raise ExportServiceError(403, "export_access_denied", "Export job access denied")
        return job
    except ExportServiceError as error:
        raise_service_error(error)


@router.get("/{job_id}/artifact")
async def download_artifact(
    job_id: UUID,
    principal: Annotated[AuthenticatedPrincipal, Depends(require_principal)],
    service: Annotated[ExportService, Depends(get_export_service)],
) -> Response:
    try:
        content, content_type, filename = await service.download_artifact(job_id, principal)
        return Response(
            content=content,
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except ExportServiceError as error:
        raise_service_error(error)
