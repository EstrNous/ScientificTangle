from uuid import uuid4

from app.service.chat_service import ChatService

from shared.contracts import UserRole
from shared.security import AuthenticatedPrincipal


def test_map_query_response_includes_live_fields() -> None:
    principal = AuthenticatedPrincipal(user_id=uuid4(), role=UserRole.ANALYST, token_id=uuid4())
    payload = ChatService._map_query_response(
        {
            "id": "run-1",
            "retrieval_trace": {"retrieved": 2, "accessible": 1},
            "warnings": ["needs_review"],
            "auth_context": {"user_id": str(principal.user_id), "role": "analyst", "access_scope": ["public", "internal"]},
            "evidence_bundle": {
                "conflicts": ["value mismatch"],
                "gaps": ["missing geo"],
                "evidence_items": [
                    {
                        "source_span": {
                            "id": "span-42",
                            "document_id": "doc-1",
                            "page": 3,
                            "text": "sample",
                            "start_offset": 0,
                            "end_offset": 6,
                            "source_type": "text",
                        }
                    }
                ],
            },
            "answer": {
                "answer_text": "Ответ",
                "confidence": 0.7,
                "scientific_answer": {"short_answer": "Ответ"},
            },
            "query_ir": {"entities": ["никель"]},
        },
        principal,
    )
    assert payload["retrieval_trace"]["retrieved"] == 2
    assert payload["query_run_id"] == "run-1"
    assert payload["scientific_answer"]["short_answer"] == "Ответ"
    assert payload["sources"][0]["source_span_id"] == "span-42"
    assert payload["conflicts"] == ["value mismatch"]
    assert payload["auth_context"]["access_scope"] == ["public", "internal"]
