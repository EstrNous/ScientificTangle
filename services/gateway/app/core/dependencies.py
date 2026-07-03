from fastapi import Request

from app.service.service import GatewayService


def get_gateway_service(request: Request) -> GatewayService:
    return request.app.state.gateway_service
