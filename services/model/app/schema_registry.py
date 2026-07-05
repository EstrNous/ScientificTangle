
from pydantic import BaseModel

from .contracts import (
    AnswerSynthesisResponse,
    ConflictDetectionResponse,
    EmbeddingResponse,
    GapSuggestionResponse,
    JsonLdEnrichmentResponse,
    NotificationMatchResponse,
    QueryIRBuildResponse,
    RerankResponse,
    SchemaEntry,
    StructuredExtractionResponse,
    UserInterestExtractionResponse,
)

SCHEMA_MODELS: dict[str, tuple[str, type[BaseModel]]] = {
    "embeddings": ("embeddings.v1", EmbeddingResponse),
    "structured_extraction": ("structured_extraction.v1", StructuredExtractionResponse),
    "query_ir": ("query_ir.v1", QueryIRBuildResponse),
    "rerank": ("rerank.v1", RerankResponse),
    "answer_synthesis": ("answer_synthesis.v1", AnswerSynthesisResponse),
    "conflict_detection": ("conflict_detection.v1", ConflictDetectionResponse),
    "gap_suggestions": ("gap_suggestions.v1", GapSuggestionResponse),
    "user_interests": ("user_interests.v1", UserInterestExtractionResponse),
    "notification_matching": ("notification_matching.v1", NotificationMatchResponse),
    "jsonld_enrichment": ("jsonld_enrichment.v1", JsonLdEnrichmentResponse),
}


def load_schema_registry() -> list[SchemaEntry]:
    return [
        SchemaEntry(name=name, version=version, json_schema=model.model_json_schema())
        for name, (version, model) in SCHEMA_MODELS.items()
    ]
