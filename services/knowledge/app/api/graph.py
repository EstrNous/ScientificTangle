from adapters.dto import (
    BootstrapResultDTO,
    EvidenceRecordDTO,
    FactVersionHistoryDTO,
    GraphExactSearchResultDTO,
    GraphNeighborhood,
    GraphSubgraphDTO,
    GroupComparisonDTO,
    MeasurementAggregateDTO,
    NeighborhoodFallbackResultDTO,
    RankedClaimDTO,
)
from adapters.neo4j_adapter import Neo4jKnowledgeAdapter
from adapters.schema import reset_database, seed_schema_registry
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from shared.contracts import GraphSubgraph, QueryIR
from shared.utils.request_id import generate_request_id

from ..storage import KnowledgeStorageAdapter, StorageAdapterNotReady

router = APIRouter(prefix="/v1/graph", tags=["graph"])

class SubgraphRequest(BaseModel):
    claim_ids: list[str] = Field(default_factory=list)
    entity_ids: list[str] = Field(default_factory=list)
    source_span_ids: list[str] = Field(default_factory=list)


class ResolveAliasRequest(BaseModel):
    mention: str = Field(min_length=1)


class ResolveAliasResponse(BaseModel):
    entity_ids: list[str]


class ConflictsRequest(BaseModel):
    entity_id: str = Field(min_length=1)


class GapsRequest(BaseModel):
    domain_profile: str = "mining-metallurgy"


class FindEntitiesRequest(BaseModel):
    name: str | None = None
    domain_type: str | None = None
    limit: int = Field(default=50, ge=1, le=200)


class FindEntitiesResponse(BaseModel):
    entity_ids: list[str]


class FilterConstraintsRequest(BaseModel):
    query_ir: QueryIR
    access_levels: list[str] = Field(default_factory=lambda: ["public", "internal"])


class AggregateMeasurementsRequest(BaseModel):
    entity_id: str | None = None


class CompareGroupsRequest(BaseModel):
    group_a_key: str = Field(min_length=1)
    group_b_key: str = Field(min_length=1)


class RetrieveEvidenceRequest(BaseModel):
    query_ir: QueryIR
    access_levels: list[str] = Field(default_factory=lambda: ["public", "internal"])


class RankClaimsRequest(BaseModel):
    claim_ids: list[str] = Field(min_length=1)
    query_ir: QueryIR | None = None
    limit: int = Field(default=20, ge=1, le=100)


class FactVersionsRequest(BaseModel):
    claim_id: str = Field(min_length=1)


class NeighborhoodFallbackRequest(BaseModel):
    query_ir: QueryIR
    access_levels: list[str] = Field(default_factory=lambda: ["public", "internal"])


class GraphExactSearchRequest(BaseModel):
    query_ir: QueryIR
    access_levels: list[str] = Field(default_factory=lambda: ["public", "internal"])


class ResetGraphResponse(BaseModel):
    reset: bool
    bootstrap: BootstrapResultDTO


@router.post("/bootstrap", response_model=BootstrapResultDTO)
async def bootstrap_graph(app_request: Request) -> BootstrapResultDTO:
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    adapter: Neo4jKnowledgeAdapter = app_request.app.state.neo4j_adapter
    return await seed_schema_registry(adapter._driver, request_id=request_id)


@router.post("/reset", response_model=ResetGraphResponse)
async def reset_graph(app_request: Request) -> ResetGraphResponse:
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    adapter: Neo4jKnowledgeAdapter = app_request.app.state.neo4j_adapter
    await reset_database(adapter._driver, request_id=request_id)
    bootstrap = await seed_schema_registry(adapter._driver, request_id=request_id)
    return ResetGraphResponse(reset=True, bootstrap=bootstrap)
  
@router.post("/subgraph", response_model=GraphSubgraph)
async def build_subgraph(
    payload: SubgraphRequest,
    request: Request,
) -> GraphSubgraph:
    adapter: KnowledgeStorageAdapter = request.app.state.storage_adapter
    try:
        return await adapter.build_subgraph(
            payload.claim_ids,
            payload.entity_ids,
            payload.source_span_ids,
        )
    except StorageAdapterNotReady as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
        

@router.get("/neighbors/{entity_id}", response_model=GraphNeighborhood)
async def expand_neighbors(entity_id: str, app_request: Request, depth: int = 1) -> GraphNeighborhood:
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    adapter: Neo4jKnowledgeAdapter = app_request.app.state.neo4j_adapter
    return await adapter.expand_neighbors(entity_id, depth=depth, request_id=request_id)


@router.post("/resolve-alias", response_model=ResolveAliasResponse)
async def resolve_alias(request: ResolveAliasRequest, app_request: Request) -> ResolveAliasResponse:
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    adapter: Neo4jKnowledgeAdapter = app_request.app.state.neo4j_adapter
    entity_ids = await adapter.resolve_aliases(request.mention, request_id=request_id)
    return ResolveAliasResponse(entity_ids=entity_ids)


@router.post("/conflicts")
async def find_conflicts(request: ConflictsRequest, app_request: Request):
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    adapter: Neo4jKnowledgeAdapter = app_request.app.state.neo4j_adapter
    return await adapter.find_conflicts(request.entity_id, request_id=request_id)


@router.post("/gaps")
async def find_gaps(request: GapsRequest, app_request: Request):
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    adapter: Neo4jKnowledgeAdapter = app_request.app.state.neo4j_adapter
    return await adapter.find_missing_edges(request.domain_profile, request_id=request_id)


@router.post("/entities", response_model=FindEntitiesResponse)
async def find_entities(request: FindEntitiesRequest, app_request: Request) -> FindEntitiesResponse:
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    adapter: Neo4jKnowledgeAdapter = app_request.app.state.neo4j_adapter
    entity_ids = await adapter.find_entities(
        name=request.name,
        domain_type=request.domain_type,
        limit=request.limit,
        request_id=request_id,
    )
    return FindEntitiesResponse(entity_ids=entity_ids)


@router.post("/filter", response_model=GraphSubgraphDTO)
async def filter_by_constraints(request: FilterConstraintsRequest, app_request: Request) -> GraphSubgraphDTO:
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    adapter: Neo4jKnowledgeAdapter = app_request.app.state.neo4j_adapter
    return await adapter.filter_by_constraints(request.query_ir, request.access_levels, request_id=request_id)


@router.post("/measurements/aggregate", response_model=list[MeasurementAggregateDTO])
async def aggregate_measurements(request: AggregateMeasurementsRequest, app_request: Request) -> list[MeasurementAggregateDTO]:
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    adapter: Neo4jKnowledgeAdapter = app_request.app.state.neo4j_adapter
    return await adapter.aggregate_measurements(request.entity_id, request_id=request_id)


@router.post("/measurements/compare", response_model=GroupComparisonDTO)
async def compare_groups(request: CompareGroupsRequest, app_request: Request) -> GroupComparisonDTO:
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    adapter: Neo4jKnowledgeAdapter = app_request.app.state.neo4j_adapter
    return await adapter.compare_groups(request.group_a_key, request.group_b_key, request_id=request_id)


@router.post("/evidence", response_model=list[EvidenceRecordDTO])
async def retrieve_evidence(request: RetrieveEvidenceRequest, app_request: Request) -> list[EvidenceRecordDTO]:
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    adapter: Neo4jKnowledgeAdapter = app_request.app.state.neo4j_adapter
    return await adapter.retrieve_evidence(request.query_ir, request.access_levels, request_id=request_id)


@router.post("/claims/rank", response_model=list[RankedClaimDTO])
async def rank_claims(request: RankClaimsRequest, app_request: Request) -> list[RankedClaimDTO]:
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    adapter: Neo4jKnowledgeAdapter = app_request.app.state.neo4j_adapter
    return await adapter.rank_claims(
        request.claim_ids,
        query_ir=request.query_ir,
        request_id=request_id,
        limit=request.limit,
    )


@router.post("/claims/versions", response_model=FactVersionHistoryDTO)
async def get_fact_versions(request: FactVersionsRequest, app_request: Request) -> FactVersionHistoryDTO:
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    adapter: Neo4jKnowledgeAdapter = app_request.app.state.neo4j_adapter
    return await adapter.get_fact_versions(request.claim_id, request_id=request_id)


@router.post("/neighborhood-fallback", response_model=NeighborhoodFallbackResultDTO)
async def neighborhood_fallback(
    request: NeighborhoodFallbackRequest,
    app_request: Request,
) -> NeighborhoodFallbackResultDTO:
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    adapter: Neo4jKnowledgeAdapter = app_request.app.state.neo4j_adapter
    return await adapter.neighborhood_fallback(
        request.query_ir,
        request.access_levels,
        request_id=request_id,
    )


@router.post("/exact-search", response_model=GraphExactSearchResultDTO)
async def graph_exact_search(
    request: GraphExactSearchRequest,
    app_request: Request,
) -> GraphExactSearchResultDTO:
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    adapter: Neo4jKnowledgeAdapter = app_request.app.state.neo4j_adapter
    return await adapter.graph_exact_search(
        request.query_ir,
        request.access_levels,
        request_id=request_id,
    )
