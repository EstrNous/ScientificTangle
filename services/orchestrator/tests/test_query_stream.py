from shared.contracts import EvidenceBundle, QueryIR, UserRole
from shared.security import AuthenticatedPrincipal

from app.service.query_stream import (
    auth_context,
    build_retrieval_steps,
    format_sse_event,
    iter_answer_chunks,
    terminal_phase,
)
from uuid import uuid4


def test_auth_context_contains_access_scope() -> None:
    principal = AuthenticatedPrincipal(user_id=uuid4(), role=UserRole.RESEARCHER, token_id=uuid4())
    context = auth_context(principal)
    assert context["role"] == "researcher"
    assert context["access_scope"] == ["public", "internal"]


def test_build_retrieval_steps_from_planner_trace() -> None:
    trace = build_retrieval_steps(
        {
            "storage": "hybrid",
            "retrieved": 4,
            "accessible": 2,
            "planner": {
                "trace": [
                    {"profile": "semantic", "selected": True},
                    {"profile": "graph", "selected": False},
                ]
            },
            "channels": {"dense": 3, "lexical": 1},
        }
    )
    assert len(trace["steps"]) >= 4
    assert trace["completed"] is True


def test_terminal_phase_marks_conflicts_as_degraded() -> None:
    bundle = EvidenceBundle(query_ir=QueryIR(raw_query="x"), has_conflicts=True)
    assert terminal_phase(0.9, [], bundle) == "degraded"


def test_iter_answer_chunks_splits_text() -> None:
    chunks = iter_answer_chunks("abcdef", chunk_size=2)
    assert chunks == ["ab", "cd", "ef"]


def test_format_sse_event_prefix() -> None:
    rendered = format_sse_event({"type": "phase", "phase": "retrieval"})
    assert rendered.startswith("data: ")
    assert rendered.endswith("\n\n")
