import hashlib

from shared.contracts import SourceSpan


def compute_source_span_id(span: SourceSpan) -> str:
    raw = f"{span.document_id}:{span.page}:{span.start_offset}:{span.end_offset}:{span.table_block_id or ''}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def compute_source_span_id_from_parts(
    document_id: str,
    page: int,
    start_offset: int,
    end_offset: int,
    table_block_id: str | None = None,
) -> str:
    raw = f"{document_id}:{page}:{start_offset}:{end_offset}:{table_block_id or ''}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]
