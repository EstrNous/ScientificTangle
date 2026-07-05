from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from shared.contracts import AccessPolicy, NormalizedDocument, SourceSpan, TableBlock
from shared.web import require_internal_service

from ..normalization import enrich_normalized_document

router = APIRouter(prefix="/v1/documents", tags=["documents"])


class NormalizeDocumentRequest(BaseModel):
    title: str = Field(min_length=1)
    content: str = ""
    source_type: str = "text"
    page: int = Field(default=1, ge=1)
    table_headers: list[str] = Field(default_factory=list)
    table_rows: list[list[str]] = Field(default_factory=list)
    access_policy: AccessPolicy = Field(default_factory=AccessPolicy)


class NormalizeDocumentResponse(BaseModel):
    document: NormalizedDocument
    warnings: list[str] = Field(default_factory=list)


@router.post("/normalize", response_model=NormalizeDocumentResponse, dependencies=[Depends(require_internal_service)])
async def normalize_document(request: NormalizeDocumentRequest) -> NormalizeDocumentResponse:
    document = build_normalized_document(request)
    warnings = []
    if not request.content and not request.table_rows:
        warnings.append("Document has no text or table rows")
    return NormalizeDocumentResponse(document=document, warnings=warnings)


def build_normalized_document(request: NormalizeDocumentRequest) -> NormalizedDocument:
    document = NormalizedDocument(
        source_type=request.source_type,
        title=request.title,
        content=request.content,
        access_policy=request.access_policy,
        metadata={"normalizer": "text_table_fallback"},
    )
    source_spans = build_text_spans(document.id, request.content, request.page)
    table_blocks = build_table_blocks(document.id, request)
    table_spans = build_table_spans(table_blocks)
    document.source_spans = [*source_spans, *table_spans]
    document.table_blocks = table_blocks
    return enrich_normalized_document(document)


def build_text_spans(document_id: str, content: str, page: int) -> list[SourceSpan]:
    chunks = [chunk.strip() for chunk in content.split("\n\n") if chunk.strip()]
    if not chunks and content.strip():
        chunks = [content.strip()]
    spans = []
    offset = 0
    for chunk in chunks:
        start = content.find(chunk, offset)
        if start < 0:
            start = offset
        end = start + len(chunk)
        spans.append(build_span(document_id, page, start, end, chunk, "text"))
        offset = end
    return spans


def build_table_blocks(document_id: str, request: NormalizeDocumentRequest) -> list[TableBlock]:
    if not request.table_headers or not request.table_rows:
        return []
    return [
        TableBlock(
            document_id=document_id,
            page=request.page,
            headers=request.table_headers,
            rows=request.table_rows,
            metadata={"normalizer": "text_table_fallback"},
        )
    ]


def build_table_spans(table_blocks: list[TableBlock]) -> list[SourceSpan]:
    spans = []
    for table in table_blocks:
        text = "\n".join(" | ".join(row) for row in table.rows)
        spans.append(build_span(table.document_id, table.page, 0, len(text), text, "table", table.id))
    return spans


def build_span(
    document_id: str,
    page: int,
    start_offset: int,
    end_offset: int,
    text: str,
    source_type: Literal["text", "table", "figure", "caption"],
    table_block_id: str | None = None,
) -> SourceSpan:
    return SourceSpan(
        document_id=document_id,
        page=page,
        start_offset=start_offset,
        end_offset=end_offset,
        text=text,
        table_block_id=table_block_id,
        source_type=source_type,
    )
