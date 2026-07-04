import asyncio

import httpx
from app.service.service import GatewayService


def test_stream_query_forwards_sse_bytes() -> None:
    chunks = [
        b'data: {"type":"phase","phase":"parsing"}\n\n',
        b'data: {"type":"done","payload":{"id":"run-1"}}\n\n',
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/query/stream"
        return httpx.Response(200, content=b"".join(chunks))

    async def run() -> bytes:
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            service = GatewayService(client, "http://orchestrator", 1024)
            collected = b""
            async for chunk in service.stream_query(
                {"question": "никель", "filters": {}, "limit": 20},
                "Bearer token",
                "req-stream",
            ):
                collected += chunk
            return collected

    result = asyncio.run(run())
    assert b'"phase":"parsing"' in result
    assert b'"type":"done"' in result
