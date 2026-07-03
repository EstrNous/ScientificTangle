from pathlib import Path

from .contracts import PromptEntry

PROMPT_FILES = {
    "embeddings": ("embeddings.v1", "embeddings_v1.md"),
    "structured_extraction": ("structured_extraction.v1", "structured_extraction_v1.md"),
    "query_ir": ("query_ir.v1", "query_ir_v1.md"),
    "rerank": ("rerank.v1", "rerank_v1.md"),
    "answer_synthesis": ("answer_synthesis.v1", "answer_synthesis_v1.md"),
    "conflict_detection": ("conflict_detection.v1", "conflict_detection_v1.md"),
    "gap_suggestions": ("gap_suggestions.v1", "gap_suggestions_v1.md"),
    "user_interests": ("user_interests.v1", "user_interests_v1.md"),
    "notification_matching": ("notification_matching.v1", "notification_matching_v1.md"),
    "jsonld_enrichment": ("jsonld_enrichment.v1", "jsonld_enrichment_v1.md"),
}


def load_prompt_registry() -> list[PromptEntry]:
    prompt_dir = Path(__file__).parent / "prompts"
    prompts = []
    for name, (version, filename) in PROMPT_FILES.items():
        prompts.append(PromptEntry(name=name, version=version, text=(prompt_dir / filename).read_text(encoding="utf-8")))
    return prompts
