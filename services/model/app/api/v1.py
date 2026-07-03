from fastapi import APIRouter

from ..contracts import (
    AnswerSynthesisRequest,
    AnswerSynthesisResponse,
    ConflictDetectionRequest,
    ConflictDetectionResponse,
    EmbeddingRequest,
    EmbeddingResponse,
    GapSuggestionRequest,
    GapSuggestionResponse,
    JsonLdEnrichmentRequest,
    JsonLdEnrichmentResponse,
    ModelStatusResponse,
    NotificationMatchRequest,
    NotificationMatchResponse,
    PromptRegistryResponse,
    QueryIRBuildRequest,
    QueryIRBuildResponse,
    RerankRequest,
    RerankResponse,
    SchemaRegistryResponse,
    StructuredExtractionRequest,
    StructuredExtractionResponse,
    UserInterestExtractionRequest,
    UserInterestExtractionResponse,
)
from ..prompt_registry import load_prompt_registry
from ..schema_registry import load_schema_registry
from ..services import (
    build_embeddings,
    build_query_ir,
    build_structured_extraction,
    detect_conflicts,
    enrich_jsonld,
    extract_user_interests,
    match_notifications,
    model_status,
    rerank_evidence,
    suggest_gaps,
    synthesize_answer,
)

router = APIRouter(prefix="/v1", tags=["model-v1"])


@router.get("/schemas", response_model=SchemaRegistryResponse)
async def schemas() -> SchemaRegistryResponse:
    return SchemaRegistryResponse(schemas=load_schema_registry())


@router.get("/prompts", response_model=PromptRegistryResponse)
async def prompts() -> PromptRegistryResponse:
    return PromptRegistryResponse(prompts=load_prompt_registry())


@router.get("/status", response_model=ModelStatusResponse)
async def status() -> ModelStatusResponse:
    return model_status()


@router.post("/embeddings", response_model=EmbeddingResponse)
async def embeddings(request: EmbeddingRequest) -> EmbeddingResponse:
    return build_embeddings(request)


@router.post("/extraction/structured", response_model=StructuredExtractionResponse)
async def structured_extraction(request: StructuredExtractionRequest) -> StructuredExtractionResponse:
    return build_structured_extraction(request)


@router.post("/query-ir", response_model=QueryIRBuildResponse)
async def query_ir(request: QueryIRBuildRequest) -> QueryIRBuildResponse:
    return build_query_ir(request)


@router.post("/rerank", response_model=RerankResponse)
async def rerank(request: RerankRequest) -> RerankResponse:
    return rerank_evidence(request)


@router.post("/answers/synthesize", response_model=AnswerSynthesisResponse)
async def answer_synthesis(request: AnswerSynthesisRequest) -> AnswerSynthesisResponse:
    return synthesize_answer(request)


@router.post("/conflicts/detect", response_model=ConflictDetectionResponse)
async def conflicts(request: ConflictDetectionRequest) -> ConflictDetectionResponse:
    return detect_conflicts(request)


@router.post("/gaps/suggest", response_model=GapSuggestionResponse)
async def gaps(request: GapSuggestionRequest) -> GapSuggestionResponse:
    return suggest_gaps(request)


@router.post("/interests/extract", response_model=UserInterestExtractionResponse)
async def interests(request: UserInterestExtractionRequest) -> UserInterestExtractionResponse:
    return extract_user_interests(request)


@router.post("/notifications/match", response_model=NotificationMatchResponse)
async def notifications(request: NotificationMatchRequest) -> NotificationMatchResponse:
    return match_notifications(request)


@router.post("/jsonld/enrich", response_model=JsonLdEnrichmentResponse)
async def jsonld(request: JsonLdEnrichmentRequest) -> JsonLdEnrichmentResponse:
    return enrich_jsonld(request)
