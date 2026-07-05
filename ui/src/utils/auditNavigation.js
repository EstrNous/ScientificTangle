export function resolveAuditEventTarget(event) {
  if (!event) return { kind: 'none' };

  const details = event.details ?? {};
  const queryRunId =
    details.query_run_id ?? details.queryRunId ?? event.query_run_id ?? event.queryRunId ?? null;
  if (queryRunId) {
    return { kind: 'navigate', path: '/chat', state: { queryRunId: String(queryRunId) } };
  }

  const sourceSpanId = event.source_span_id ?? event.sourceSpanId ?? details.source_span_id ?? null;
  if (sourceSpanId) {
    return { kind: 'source', ref: String(sourceSpanId) };
  }

  const documentId =
    details.document_id ??
    details.documentId ??
    (event.resource_type === 'document' ? event.resource_id : null);
  if (documentId) {
    return {
      kind: 'navigate',
      path: '/upload',
      state: { documentId: String(documentId) },
    };
  }

  const resourceType = event.resource_type ?? event.resourceType ?? '';
  const resourceId = event.resource_id ?? event.resourceId ?? '';
  if (resourceType === 'ingestion_task' && resourceId) {
    return {
      kind: 'navigate',
      path: '/upload',
      state: { ingestionTaskId: String(resourceId) },
    };
  }

  if (resourceType === 'review_item' && resourceId) {
    return {
      kind: 'navigate',
      path: '/review',
      state: { candidateId: String(resourceId) },
    };
  }

  return { kind: 'none' };
}
