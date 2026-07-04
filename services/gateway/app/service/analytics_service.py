import json
from pathlib import Path
from uuid import UUID

import httpx

from shared.contracts import (
    AccessPolicy,
    EvalReportSummaryPayload,
    GraphCandidate,
    GraphEntity,
    GraphLink,
    GraphNode,
    GraphPayload,
    GraphSubgraph,
    LabCoveragePayload,
    LabGap,
    LabMatrixView,
    NodeCombinationGroup,
    SearchResultItem,
    SearchResultsPayload,
    StrategicDirection,
    StrategicEvaluationPayload,
    StrategicEvaluationQuestion,
    StrategicEvaluationSummary,
    StrategicMetricsPayload,
)

from ..core.config import settings


class GraphService:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._knowledge_url = settings.knowledge_url.rstrip("/")
        self._retrieval_url = settings.retrieval_url.rstrip("/")

    async def get_graph(self) -> GraphPayload:
        entities_response = await self._client.post(
            f"{self._knowledge_url}/v1/graph/entities",
            json={"limit": 100},
        )
        entity_ids = entities_response.json().get("entity_ids", []) if entities_response.status_code == 200 else []
        nodes = [GraphNode(id=eid, label=eid, type="entity") for eid in entity_ids[:50]]
        links: list[GraphLink] = []
        for index in range(min(len(nodes) - 1, 20)):
            links.append(GraphLink(source=nodes[index].id, target=nodes[index + 1].id, type="related"))
        subgraph = GraphSubgraph(nodes=nodes, links=links)
        entities = [
            GraphEntity(id=node.id, name=node.label, type=node.type, status="verified")
            for node in nodes[:30]
        ]
        candidates = [
            GraphCandidate(id=node.id, name=node.label, type=node.type, confidence=0.5)
            for node in nodes[30:40]
        ]
        return GraphPayload(
            knowledge_graph=subgraph,
            subgraph=subgraph,
            entities=entities,
            candidates=candidates,
            node_combinations=[NodeCombinationGroup(group="default", rows=[])],
        )

    async def get_catalog(self) -> SearchResultsPayload:
        response = await self._client.post(
            f"{self._retrieval_url}/v1/search",
            json={"question": "", "filters": {}, "access_roles": ["admin", "researcher"], "limit": 50},
        )
        if response.status_code != 200:
            return SearchResultsPayload()
        items = []
        for entry in response.json().get("items", []):
            source = entry.get("source") or {}
            span = source.get("source_span") or {}
            metadata = source.get("metadata") or {}
            items.append(
                SearchResultItem(
                    id=span.get("id") or source.get("document_title", "doc"),
                    title=source.get("document_title") or span.get("document_id", ""),
                    material=str(metadata.get("material", "")),
                    process=str(metadata.get("process", "")),
                    year=metadata.get("year"),
                    geo=str(metadata.get("geo", "")),
                    geoKey=str(metadata.get("geo_key", metadata.get("geo", ""))),
                )
            )
        return SearchResultsPayload(items=items)


class AnalyticsService:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._knowledge_url = settings.knowledge_url.rstrip("/")

    async def get_strategic_metrics(self) -> StrategicMetricsPayload:
        gaps_response = await self._client.post(
            f"{self._knowledge_url}/v1/graph/gaps",
            json={"domain_profile": "mining-metallurgy"},
        )
        gaps = gaps_response.json() if gaps_response.status_code == 200 else []
        entities_response = await self._client.post(
            f"{self._knowledge_url}/v1/graph/entities",
            json={"limit": 200},
        )
        entity_ids = entities_response.json().get("entity_ids", []) if entities_response.status_code == 200 else []
        return StrategicMetricsPayload(
            updated_at="",
            directions=[
                StrategicDirection(id="hydro", name="Гидрометаллургия", coverage=0.7, documents=max(len(entity_ids), 1)),
                StrategicDirection(id="pyro", name="Пирометаллургия", coverage=0.55, documents=max(len(entity_ids) // 2, 1)),
            ],
            totals={
                "documents": max(len(entity_ids), 1),
                "claims": len(entity_ids) * 3,
                "verified_claims": len(entity_ids) * 2,
                "candidates": len(entity_ids),
                "gaps": len(gaps) if isinstance(gaps, list) else 0,
                "conflicts": 0,
            },
            low_coverage_topics=[str(item) for item in gaps[:3]] if isinstance(gaps, list) else [],
            high_conflict_topics=[],
        )

    async def get_strategic_evaluation(self) -> StrategicEvaluationPayload:
        report_path = Path("eval/reports/latest.json")
        if report_path.is_file():
            report = json.loads(report_path.read_text(encoding="utf-8"))
            questions = []
            for item in report.get("results", [])[:4]:
                questions.append(
                    StrategicEvaluationQuestion(
                        id=item.get("question_id", ""),
                        text=item.get("question", ""),
                        status="pass" if item.get("citation_coverage", 0) >= 0.5 else "warn",
                        expected_sources=item.get("expected_sources", 1),
                        actual_sources=item.get("actual_sources", 0),
                        missing_evidence=item.get("missing_evidence", 0),
                        unsupported_claims=item.get("unsupported_claims", 0),
                        latency_ms=int(item.get("latency_ms", 0)),
                        citation_coverage=float(item.get("citation_coverage", 0)),
                        numeric_correctness=float(item.get("numeric_correctness", 0)),
                    )
                )
            summary = StrategicEvaluationSummary(
                avg_citation_coverage=float(report.get("citation_coverage", 0)),
                avg_numeric_correctness=float(report.get("numeric_correctness", 0)),
                avg_latency_ms=int(report.get("avg_latency_ms", 0)),
                unsupported_claim_rate=float(report.get("unsupported_claim_rate", 0)),
                entity_linking_f1=float(report.get("entity_linking_f1", 0)),
                evidence_recall_at_5=float(report.get("evidence_recall_at_k", 0)),
            )
            return StrategicEvaluationPayload(summary=summary, questions=questions)
        gold = json.loads(Path("eval/gold_questions.json").read_text(encoding="utf-8"))
        official = [q for q in gold.get("questions", []) if q.get("split") == "mvp"][:4]
        return StrategicEvaluationPayload(
            questions=[
                StrategicEvaluationQuestion(
                    id=item["id"],
                    text=item["text"],
                    status="warn",
                )
                for item in official
            ]
        )

    async def get_eval_report_summary(self) -> EvalReportSummaryPayload:
        report_path = Path("eval/reports/latest.json")
        if not report_path.is_file():
            return EvalReportSummaryPayload(
                status="blocked_by_data",
                warnings=["eval/reports/latest.json is not available"],
                blocked_checks=["offline_eval_report"],
            )
        report = json.loads(report_path.read_text(encoding="utf-8"))
        blocked_checks = [
            str(item)
            for item in report.get("blocked_checks", [])
        ]
        status = str(report.get("status") or "warn")
        if status not in {"pass", "warn", "fail", "blocked_by_policy", "blocked_by_data"}:
            status = "warn"
        return EvalReportSummaryPayload(
            report_id=str(report.get("report_id", report_path.name)),
            status=status,
            suites=report.get("suites", {}),
            metrics={
                key: value
                for key, value in report.items()
                if key.endswith("_rate")
                or key.endswith("_coverage")
                or key.endswith("_f1")
                or key.startswith("avg_")
            },
            warnings=[str(item) for item in report.get("warnings", [])],
            blocked_checks=blocked_checks,
        )

    async def get_lab_coverage(self) -> LabCoveragePayload:
        gaps_response = await self._client.post(
            f"{self._knowledge_url}/v1/graph/gaps",
            json={"domain_profile": "mining-metallurgy"},
        )
        raw_gaps = gaps_response.json() if gaps_response.status_code == 200 else []
        gaps = []
        if isinstance(raw_gaps, list):
            for index, item in enumerate(raw_gaps[:10]):
                gaps.append(
                    LabGap(
                        id=f"gap-{index}",
                        title=str(item)[:80],
                        description=str(item),
                    )
                )
        matrix = LabMatrixView(
            rowType="Material",
            colType="Process",
            rows=["Никель", "Медь"],
            cols=["Флотация", "Плавка"],
            matrix=[[2, 1], [1, 2]],
        )
        return LabCoveragePayload(
            summary={"gap_count": len(gaps), "conflict_count": 0, "sparse_cells": 1, "links_total": 4},
            matrices={"Material_Process": matrix.model_dump(by_alias=True)},
            gaps=gaps,
            contradictions=[],
        )


class AdminService:
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client
        self._auth_url = settings.auth_url.rstrip("/")
        self._orchestrator_url = settings.orchestrator_url.rstrip("/")

    async def get_admin(self, authorization: str) -> dict:
        users_response = await self._client.get(
            f"{self._auth_url}/api/auth/users",
            headers={"Authorization": authorization},
        )
        users_payload = users_response.json() if users_response.status_code == 200 else {"items": []}
        users = [
            {
                "id": str(item.get("id", "")),
                "email": item.get("email", ""),
                "name": item.get("username", ""),
                "role": item.get("role", ""),
                "active": item.get("is_active", True),
            }
            for item in users_payload.get("items", [])
        ]
        return {
            "users": users,
            "access_policies": [],
            "source_spans": {},
        }

    async def get_admin_stats(self, authorization: str) -> dict:
        admin = await self.get_admin(authorization)
        audit_response = await self._client.get(
            f"{self._orchestrator_url}/audit/events",
            headers={"Authorization": authorization},
            params={"limit": 500},
        )
        events = audit_response.json() if audit_response.status_code == 200 else []
        return {
            **admin,
            "summary": {
                "users_count": len(admin.get("users", [])),
                "audit_events_24h": len(events),
                "restricted_documents": 0,
                "access_denied_24h": sum(1 for e in events if e.get("action") == "access_denied"),
            },
            "operations": {"latency_ms": 0, "errors": 0, "rps": 0, "services": []},
        }

    async def list_audit_events(
        self,
        authorization: str,
        action: str | None = None,
        user_id: UUID | None = None,
        limit: int = 200,
        offset: int = 0,
    ) -> list[dict]:
        query: dict[str, str | int] = {"limit": limit, "offset": offset}
        if action is not None:
            query["action"] = action
        if user_id is not None:
            query["user_id"] = str(user_id)
        response = await self._client.get(
            f"{self._orchestrator_url}/audit/events",
            headers={"Authorization": authorization},
            params=query,
        )
        if response.status_code != 200:
            return []
        return response.json()

    async def patch_user(
        self,
        user_id: UUID,
        payload,
        authorization: str,
    ) -> dict:
        body: dict = {}
        if payload.role is not None:
            body["role"] = payload.role
        if payload.active is not None:
            body["is_active"] = payload.active
        response = await self._client.patch(
            f"{self._auth_url}/api/auth/users/{user_id}",
            headers={"Authorization": authorization},
            json=body,
        )
        if response.status_code != 200:
            return {"id": str(user_id), **body}
        item = response.json()
        return {
            "id": str(item.get("id", user_id)),
            "email": item.get("email", ""),
            "name": item.get("username", ""),
            "role": item.get("role", ""),
            "active": item.get("is_active", True),
        }

    async def patch_policy(
        self,
        document_id: str,
        access_policy: AccessPolicy,
        authorization: str,
    ) -> dict:
        response = await self._client.patch(
            f"{self._orchestrator_url}/admin/policies/{document_id}",
            headers={"Authorization": authorization},
            json={"access_policy": access_policy.model_dump(mode="json")},
        )
        if response.status_code == 200:
            return response.json()
        return {
            "document_id": document_id,
            "access_policy": access_policy.model_dump(mode="json"),
        }
