from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from adapters.dto import BootstrapResultDTO, GraphNeighborhood, GraphSubgraphDTO
from adapters.neo4j_adapter import Neo4jKnowledgeAdapter
from adapters.schema import reset_database, seed_schema_registry
from shared.contracts import QueryIR
from shared.utils.request_id import generate_request_id

router = APIRouter(prefix="/v1/graph", tags=["graph"])


class SubgraphRequest(BaseModel):
    query_ir: QueryIR
    access_levels: list[str] = Field(default_factory=lambda: ["public", "internal"])


class ResolveAliasRequest(BaseModel):
    mention: str = Field(min_length=1)


class ResolveAliasResponse(BaseModel):
    entity_ids: list[str]


class ConflictsRequest(BaseModel):
    entity_id: str = Field(min_length=1)


class GapsRequest(BaseModel):
    domain_profile: str = "mining-metallurgy"


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


@router.post("/subgraph", response_model=GraphSubgraphDTO)
async def build_subgraph(request: SubgraphRequest, app_request: Request) -> GraphSubgraphDTO:
    request_id = getattr(app_request.state, "request_id", None) or generate_request_id()
    adapter: Neo4jKnowledgeAdapter = app_request.app.state.neo4j_adapter
    return await adapter.build_subgraph(request.query_ir, request.access_levels, request_id=request_id)


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
