import json
from uuid import UUID

from infra.postgres.chat_ui_db.repository import ChatRepository
from infra.postgres.notification_db.repository import NotificationData, NotificationRepository
from shared.security import AuthenticatedPrincipal

from .service import GatewayService, GatewayServiceError


class ChatServiceError(Exception):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(message)


class ChatService:
    def __init__(
        self,
        repository: ChatRepository,
        gateway_service: GatewayService,
        notification_repository: NotificationRepository | None = None,
    ) -> None:
        self._repository = repository
        self._gateway_service = gateway_service
        self._notification_repository = notification_repository

    async def list_sessions(self, principal: AuthenticatedPrincipal) -> list[dict]:
        sessions = await self._repository.list_sessions(principal.user_id)
        return [self._session_payload(session) for session in sessions]

    async def create_session(self, principal: AuthenticatedPrincipal, title: str) -> dict:
        session = await self._repository.create_session(principal.user_id, title.strip())
        return self._session_payload(session)

    async def delete_session(self, principal: AuthenticatedPrincipal, session_id: UUID) -> None:
        deleted = await self._repository.delete_session(session_id, principal.user_id)
        if not deleted:
            raise ChatServiceError(404, "session_not_found", "Chat session not found")

    async def list_messages(self, principal: AuthenticatedPrincipal, session_id: UUID) -> list[dict]:
        await self._require_session(principal, session_id)
        messages = await self._repository.get_messages(session_id)
        return [self._message_payload(message) for message in messages]

    async def send_message(
        self,
        principal: AuthenticatedPrincipal,
        session_id: UUID,
        content: str,
        authorization: str,
        request_id: str,
    ) -> dict:
        await self._require_session(principal, session_id)
        await self._repository.save_message(session_id, "user", content.strip())

        try:
            query_response = await self._gateway_service.run_query(
                {"question": content.strip(), "filters": {}, "limit": 20},
                authorization,
                request_id,
            )
        except GatewayServiceError as error:
            raise ChatServiceError(error.status_code, error.code, error.message) from error

        await self._maybe_notify_conflicts(principal, query_response)
        assistant_payload = self._map_query_response(query_response, principal)
        saved = await self._repository.save_message(
            session_id,
            "assistant",
            json.dumps(assistant_payload, ensure_ascii=False),
        )
        return self._message_payload(saved)

    async def _maybe_notify_conflicts(
        self,
        principal: AuthenticatedPrincipal,
        query_response: dict,
    ) -> None:
        if self._notification_repository is None:
            return
        evidence_bundle = query_response.get("evidence_bundle") or {}
        conflicts = evidence_bundle.get("conflicts") or []
        if not conflicts:
            return
        run_id = query_response.get("id")
        await self._notification_repository.create_notification(
            NotificationData(
                user_id=principal.user_id,
                type="conflict_detected",
                message="Обнаружено противоречие в ответе на запрос",
                reference_id=str(run_id) if run_id else None,
            )
        )

    async def _require_session(self, principal: AuthenticatedPrincipal, session_id: UUID) -> None:
        session = await self._repository.get_session(session_id, principal.user_id)
        if session is None:
            raise ChatServiceError(404, "session_not_found", "Chat session not found")

    @staticmethod
    def _session_payload(session) -> dict:
        return {
            "id": str(session.id),
            "title": session.title,
            "updated_at": session.updated_at.isoformat(),
            "created_at": session.created_at.isoformat(),
        }

    @classmethod
    def _message_payload(cls, message) -> dict:
        if message.role == "assistant":
            try:
                payload = json.loads(message.content)
                if isinstance(payload, dict):
                    return {
                        "id": str(message.id),
                        "role": "assistant",
                        **payload,
                    }
            except (TypeError, ValueError):
                pass
        return {
            "id": str(message.id),
            "role": message.role,
            "content": message.content,
        }

    @classmethod
    def _map_query_response(cls, query_response: dict, principal: AuthenticatedPrincipal) -> dict:
        answer = query_response.get("answer") or {}
        evidence_bundle = query_response.get("evidence_bundle") or answer.get("evidence_bundle") or {}
        query_ir = query_response.get("query_ir") or answer.get("query_ir") or {}
        evidence_items = evidence_bundle.get("evidence_items") or []
        retrieval_trace = query_response.get("retrieval_trace") or {}

        sources = []
        rows = []
        for item in evidence_items:
            span = item.get("source_span") or {}
            span_id = span.get("id") or span.get("document_id") or "source"
            document_id = span.get("document_id") or "source"
            snippet = (span.get("text") or "").strip()
            sources.append(
                {
                    "title": document_id,
                    "author": document_id,
                    "date": "",
                    "confidence_level": "verified",
                    "source_span_id": span_id,
                    "document_id": document_id,
                    "page": span.get("page"),
                }
            )
            if snippet:
                rows.append(
                    [
                        f"Стр. {span.get('page', '—')}",
                        snippet[:160],
                        span_id,
                    ]
                )

        entities = query_ir.get("entities") or []
        scientific_answer = answer.get("scientific_answer")
        auth_context = query_response.get("auth_context") or {
            "user_id": str(principal.user_id),
            "role": principal.role.value,
        }
        return {
            "content": answer.get("answer_text") or "Ответ не сформирован.",
            "confidence": float(answer.get("confidence") or 0.0),
            "sources": sources,
            "expanded_synonyms": entities,
            "evidence_table": {
                "columns": ["Параметр", "Фрагмент", "Источник"],
                "rows": rows[:8],
            },
            "warnings": query_response.get("warnings") or [],
            "retrieval_trace": retrieval_trace,
            "query_run_id": str(query_response.get("id") or ""),
            "scientific_answer": scientific_answer,
            "auth_context": auth_context,
            "conflicts": evidence_bundle.get("conflicts") or [],
            "gaps": evidence_bundle.get("gaps") or [],
        }
