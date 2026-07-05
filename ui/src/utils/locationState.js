export function resolveIngestionTaskIdFromState(state) {
  if (!state) return null;
  const value =
    state.ingestionTaskId ??
    state.ingestion_task_id ??
    state.taskId ??
    state.task_id ??
    null;
  return value != null && value !== '' ? String(value) : null;
}

export function resolveDocumentIdFromState(state) {
  if (!state) return null;
  const value = state.documentId ?? state.document_id ?? null;
  return value != null && value !== '' ? String(value) : null;
}

export function resolveQueryRunIdFromState(state) {
  if (!state) return null;
  const value = state.queryRunId ?? state.query_run_id ?? null;
  return value != null && value !== '' ? String(value) : null;
}

export function resolveCandidateIdFromState(state) {
  if (!state) return null;
  const value = state.candidateId ?? state.candidate_id ?? state.itemId ?? state.item_id ?? null;
  return value != null && value !== '' ? String(value) : null;
}

export function clearNavigationState(navigate, pathname) {
  navigate(pathname, { replace: true, state: null });
}
