from fastapi import APIRouter

from shared.contracts import (
    RetrievalIndexRequest,
    RetrievalIndexResponse,
    StorageWriteResult,
)

router = APIRouter(prefix="/v1/documents", tags=["retrieval-indexing"])


@router.post("/index", response_model=RetrievalIndexResponse)
async def index_documents(request: RetrievalIndexRequest) -> RetrievalIndexResponse:
    warning = "qdrant_adapter_pending"
    records_count = sum(
        sum(span.source_type != "table" for span in document.source_spans)
        + sum(len(table.rows) + bool(table.headers) for table in document.table_blocks)
        for document in request.documents
    )
    return RetrievalIndexResponse(
        vector_write=StorageWriteResult(
            backend="qdrant",
            document_ids=[document.id for document in request.documents],
            records_count=records_count,
            warnings=[warning],
        ),
        warnings=[warning],
    )
