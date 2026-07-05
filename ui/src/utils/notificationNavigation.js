export function resolveNotificationTarget(item) {
  const referenceId = item.referenceId ?? item.reference_id ?? null;
  const referenceType = item.referenceType ?? item.reference_type ?? 'document';

  if (!referenceId) {
    if (referenceType === 'review_item') {
      return { kind: 'navigate', path: '/review' };
    }
    return { kind: 'none' };
  }

  if (referenceType === 'source_span') {
    return { kind: 'source', ref: referenceId };
  }
  if (referenceType === 'document') {
    return { kind: 'source', ref: referenceId };
  }
  if (referenceType === 'query_run') {
    return { kind: 'navigate', path: '/chat', state: { queryRunId: referenceId } };
  }
  if (referenceType === 'ingestion_task') {
    return { kind: 'navigate', path: '/upload', state: { ingestionTaskId: referenceId } };
  }
  if (referenceType === 'review_item') {
    return { kind: 'navigate', path: '/review', state: { candidateId: referenceId } };
  }
  return { kind: 'none' };
}

export function notificationTitleKey(type) {
  if (!type) return null;
  return `notifications.types.${type}`;
}
