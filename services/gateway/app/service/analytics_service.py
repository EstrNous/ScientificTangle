import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
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

HYDRO_MARKERS = ("гидро", "hydro", "leach", "выщел", "adsorp", "сорб")
PYRO_MARKERS = ("пиро", "pyro", "smelt", "плав", "roast", "обжиг", "конверт")


def gap_topic_label(item: Any) -> str:
    if isinstance(item, dict):
        description = str(item.get("description") or "").strip()
        if description:
            return description
        return str(item.get("gap_id") or "").strip()
    return str(item).strip()


def map_lab_gap(item: Any, index: int) -> LabGap:
    if isinstance(item, dict):
        description = str(item.get("description") or "").strip()
        gap_id = str(item.get("gap_id") or f"gap-{index}")
        expected = str(item.get("expected_relation") or "").strip()
        entity_ids = [str(value) for value in item.get("entity_ids") or [] if value]
        priority = str(item.get("priority") or "medium")
        title = description[:80] if description else f"Пробел знаний {index + 1}"
        constraints = [tag for tag in (expected, priority) if tag]
        if entity_ids:
            constraints.append(f"Сущности: {', '.join(entity_ids[:3])}")
        return LabGap(
            id=gap_id,
            title=title,
            description=description or title,
            constraints=constraints,
        )
    text = str(item).strip()
    return LabGap(
        id=f"gap-{index}",
        title=text[:80] or f"Пробел знаний {index + 1}",
        description=text or f"Пробел знаний {index + 1}",
    )


def direction_group(name: str) -> str | None:
    lowered = name.casefold()
    if any(marker in lowered for marker in HYDRO_MARKERS):
        return "hydro"
    if any(marker in lowered for marker in PYRO_MARKERS):
        return "pyro"
    return None


def build_directions(process_rows: list[dict[str, Any]]) -> list[StrategicDirection]:
    grouped: dict[str, dict[str, int]] = {
        "hydro": {"processes": 0, "covered": 0, "documents": 0},
        "pyro": {"processes": 0, "covered": 0, "documents": 0},
    }
    for row in process_rows:
        group = direction_group(str(row.get("name") or ""))
        if group is None:
            continue
        grouped[group]["processes"] += 1
        if int(row.get("claim_count") or 0) > 0:
            grouped[group]["covered"] += 1
        grouped[group]["documents"] += int(row.get("document_count") or 0)
    directions = [
        StrategicDirection(
            id="hydro",
            name="Гидрометаллургия",
            coverage=round(grouped["hydro"]["covered"] / grouped["hydro"]["processes"], 2)
            if grouped["hydro"]["processes"]
            else 0.0,
            documents=grouped["hydro"]["documents"],
        ),
        StrategicDirection(
            id="pyro",
            name="Пирометаллургия",
            coverage=round(grouped["pyro"]["covered"] / grouped["pyro"]["processes"], 2)
            if grouped["pyro"]["processes"]
            else 0.0,
            documents=grouped["pyro"]["documents"],
        ),
    ]
    if not any(direction.coverage > 0 or direction.documents > 0 for direction in directions):
        return []
    return directions


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
        self._retrieval_url = settings.retrieval_url.rstrip("/")

    async def _fetch_graph_stats(self) -> dict[str, int]:
        response = await self._client.get(f"{self._knowledge_url}/v1/graph/stats")
        if response.status_code != 200:
            return {}
        payload = response.json()
        return {
            "documents": int(payload.get("documents") or 0),
            "claims": int(payload.get("claims") or 0),
            "verified_claims": int(payload.get("verified_claims") or 0),
            "candidates": int(payload.get("candidates") or 0),
            "conflicts": int(payload.get("conflicts") or 0),
        }

    async def _fetch_process_rows(self) -> list[dict[str, Any]]:
        response = await self._client.get(f"{self._knowledge_url}/v1/graph/process-directions")
        if response.status_code != 200:
            return []
        payload = response.json()
        if not isinstance(payload, list):
            return []
        return [
            {
                "name": str(item.get("name") or ""),
                "document_count": int(item.get("document_count") or 0),
                "claim_count": int(item.get("claim_count") or 0),
            }
            for item in payload
            if isinstance(item, dict)
        ]

    async def _fetch_gaps(self) -> list[Any]:
        response = await self._client.post(
            f"{self._knowledge_url}/v1/graph/gaps",
            json={"domain_profile": "mining-metallurgy"},
        )
        if response.status_code != 200:
            return []
        payload = response.json()
        return payload if isinstance(payload, list) else []

    async def _fetch_index_points(self) -> int:
        response = await self._client.get(f"{self._retrieval_url}/v1/index/status")
        if response.status_code != 200:
            return 0
        return int(response.json().get("points_count") or 0)

    async def get_strategic_metrics(self) -> StrategicMetricsPayload:
        stats = await self._fetch_graph_stats()
        gaps = await self._fetch_gaps()
        process_rows = await self._fetch_process_rows()
        directions = build_directions(process_rows)
        indexed_points = await self._fetch_index_points()
        totals = {
            "documents": stats.get("documents", 0),
            "claims": stats.get("claims", 0),
            "verified_claims": stats.get("verified_claims", 0),
            "candidates": stats.get("candidates", 0),
            "gaps": len(gaps),
            "conflicts": stats.get("conflicts", 0),
        }
        metric_sources = {
            "documents": ["knowledge:/v1/graph/stats"],
            "claims": ["knowledge:/v1/graph/stats"],
            "verified_claims": ["knowledge:/v1/graph/stats"],
            "candidates": ["knowledge:/v1/graph/stats"],
            "gaps": ["knowledge:/v1/graph/gaps"],
            "conflicts": ["knowledge:/v1/graph/stats"],
        }
        if indexed_points > 0:
            metric_sources["documents"].append("retrieval:/v1/index/status")
        return StrategicMetricsPayload(
            updated_at=datetime.now(UTC).isoformat(),
            directions=directions,
            totals=totals,
            low_coverage_topics=[gap_topic_label(item) for item in gaps[:3] if gap_topic_label(item)],
            high_conflict_topics=[],
            metric_sources=metric_sources,
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
        gold_path = Path("eval/gold_questions.json")
        if not gold_path.is_file():
            return StrategicEvaluationPayload()
        gold = json.loads(gold_path.read_text(encoding="utf-8"))
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
        raw_gaps = await self._fetch_gaps()
        gaps = [map_lab_gap(item, index) for index, item in enumerate(raw_gaps[:10])]
        stats = await self._fetch_graph_stats()
        matrix = LabMatrixView(
            rowType="Material",
            colType="Process",
            rows=["Никель", "Медь"],
            cols=["Флотация", "Плавка"],
            matrix=[[0, 0], [0, 0]],
        )
        if stats.get("documents", 0) > 0:
            matrix = LabMatrixView(
                rowType="Material",
                colType="Process",
                rows=["Никель", "Медь"],
                cols=["Флотация", "Плавка"],
                matrix=[[1, 1], [1, 1]],
            )
        return LabCoveragePayload(
            summary={
                "gap_count": len(gaps),
                "conflict_count": stats.get("conflicts", 0),
                "sparse_cells": max(len(gaps), 0),
                "links_total": stats.get("claims", 0),
            },
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
        documents_response = await self._client.get(
            f"{self._orchestrator_url}/documents",
            headers={"Authorization": authorization},
            params={"limit": 200},
        )
        access_policies = []
        if documents_response.status_code == 200:
            for item in documents_response.json().get("items", []):
                access_policies.append(
                    {
                        "document_id": item.get("document_id"),
                        "title": item.get("title", ""),
                        "level": item.get("access_level", "internal"),
                        "access_policy": {
                            "level": item.get("access_level", "internal"),
                            "allowed_roles": [],
                        },
                    }
                )
        return {
            "users": users,
            "access_policies": access_policies,
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
        restricted_documents = sum(
            1
            for policy in admin.get("access_policies", [])
            if policy.get("level") in {"restricted", "confidential"}
        )
        return {
            **admin,
            "summary": {
                "users_count": len(admin.get("users", [])),
                "audit_events_24h": len(events),
                "restricted_documents": restricted_documents,
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
