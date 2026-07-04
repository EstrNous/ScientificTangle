import asyncio
import json
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

from shared.contracts import EvidenceBundle, UserRole
from shared.security import AuthenticatedPrincipal

from .scientific_query import access_levels_for_role

QueryEventEmitter = Callable[[dict[str, Any]], Awaitable[None]]


def auth_context(principal: AuthenticatedPrincipal) -> dict[str, Any]:
    return {
        "user_id": str(principal.user_id),
        "role": principal.role.value,
        "access_scope": access_levels_for_role(principal.role),
    }


def access_scope_for_role(role: str) -> list[str]:
    try:
        return access_levels_for_role(UserRole(role))
    except ValueError:
        return ["public"]


def format_sse_event(event: dict[str, Any]) -> str:
    return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"


def build_retrieval_steps(retrieval_trace: dict[str, Any]) -> dict[str, Any]:
    steps: list[dict[str, str]] = []
    planner = retrieval_trace.get("planner")
    if isinstance(planner, dict):
        trace = planner.get("trace")
        if isinstance(trace, list):
            for item in trace:
                if not isinstance(item, dict):
                    continue
                profile = str(item.get("profile") or "retriever")
                selected = bool(item.get("selected"))
                steps.append(
                    {
                        "id": f"planner-{profile}",
                        "label": profile,
                        "status": "done" if selected else "pending",
                    }
                )
    channels = retrieval_trace.get("channels")
    if isinstance(channels, dict):
        for channel, count in channels.items():
            if not count:
                continue
            steps.append(
                {
                    "id": f"channel-{channel}",
                    "label": f"{channel}:{count}",
                    "status": "done",
                }
            )
    storage = retrieval_trace.get("storage")
    if storage:
        steps.append({"id": "storage", "label": str(storage), "status": "done"})
    retrieved = retrieval_trace.get("retrieved")
    accessible = retrieval_trace.get("accessible")
    if retrieved is not None:
        label = f"retrieved:{retrieved}"
        if accessible is not None:
            label = f"{label}/accessible:{accessible}"
        steps.append({"id": "retrieved", "label": label, "status": "done"})
    if not steps:
        return {"steps": [], "activeStepId": None, "completed": True}
    return {"steps": steps, "activeStepId": None, "completed": True}


def terminal_phase(answer_confidence: float, warnings: list[str], evidence_bundle: EvidenceBundle) -> str:
    if evidence_bundle.has_conflicts or any("conflict" in warning for warning in warnings):
        return "degraded"
    if answer_confidence < 0.6:
        return "degraded"
    if any("insufficient" in warning for warning in warnings):
        return "degraded"
    return "done"


def iter_answer_chunks(text: str, chunk_size: int = 48) -> list[str]:
    if not text:
        return []
    return [text[index : index + chunk_size] for index in range(0, len(text), chunk_size)]


async def emit_phase(on_event: QueryEventEmitter | None, phase: str) -> None:
    if on_event is None:
        return
    await on_event({"type": "phase", "phase": phase})


async def emit_retrieval_trace(on_event: QueryEventEmitter | None, retrieval_trace: dict[str, Any]) -> None:
    if on_event is None:
        return
    trace = build_retrieval_steps(retrieval_trace)
    if not trace["steps"]:
        return
    await on_event({"type": "retrieval_step", **trace})


async def emit_answer_chunks(on_event: QueryEventEmitter | None, answer_text: str) -> None:
    if on_event is None or not answer_text:
        return
    chunks = iter_answer_chunks(answer_text)
    if not chunks:
        return
    draft = ""
    for chunk in chunks:
        draft += chunk
        await on_event({"type": "answer_chunk", "chunk": draft, "complete": False})
    await on_event({"type": "answer_chunk", "chunk": answer_text, "complete": True})


async def wrap_stream_query(
    runner: Callable[[QueryEventEmitter], Awaitable[dict[str, Any]]],
    principal: AuthenticatedPrincipal,
) -> AsyncIterator[str]:
    queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

    async def on_event(event: dict[str, Any]) -> None:
        await queue.put(event)

    async def execute() -> None:
        try:
            payload = await runner(on_event)
            payload["auth_context"] = auth_context(principal)
            await on_event({"type": "done", "payload": payload})
        except Exception as error:
            code = getattr(error, "code", "query_stream_failed")
            message = getattr(error, "message", str(error))
            query_run_id = getattr(error, "query_run_id", None)
            await on_event(
                {
                    "type": "phase",
                    "phase": "error",
                    "code": code,
                    "message": message,
                    "query_run_id": str(query_run_id) if query_run_id else None,
                }
            )
        finally:
            await queue.put(None)

    task = asyncio.create_task(execute())
    while True:
        event = await queue.get()
        if event is None:
            break
        yield format_sse_event(event)
    await task
