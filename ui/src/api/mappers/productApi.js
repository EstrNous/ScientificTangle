export function mapInterest(item = {}) {
  return {
    label: item.label ?? '',
    weight: item.weight ?? 0,
    sourceTerms: item.source_terms ?? item.sourceTerms ?? [],
  };
}

export function mapInterestsProfile(payload = {}) {
  return {
    rawText: payload.raw_text ?? payload.rawText ?? '',
    interests: (payload.interests ?? []).map(mapInterest),
    extractedEntities: payload.extracted_entities ?? payload.extractedEntities ?? [],
    warnings: payload.warnings ?? [],
    updatedAt: payload.updated_at ?? payload.updatedAt ?? null,
  };
}

export function serializeInterestsUpdate({ rawText, interests }) {
  const body = {};
  if (rawText != null) {
    body.raw_text = rawText;
  }
  if (interests != null) {
    body.interests = interests.map((item) => ({
      label: item.label,
      weight: item.weight,
      source_terms: item.sourceTerms ?? item.source_terms ?? [],
    }));
  }
  return body;
}

export function mapNotification(item = {}) {
  return {
    id: item.id,
    title: item.title ?? '',
    reason: item.reason ?? item.message ?? '',
    type: item.type ?? 'unknown',
    referenceId: item.reference_id ?? item.referenceId ?? null,
    referenceType: item.reference_type ?? item.referenceType ?? null,
    read: Boolean(item.read ?? item.is_read),
    createdAt: item.created_at ?? item.createdAt ?? null,
  };
}

export function mapNotificationList(payload) {
  const items = Array.isArray(payload) ? payload : payload?.items ?? [];
  return items.map(mapNotification);
}

export function mapReviewCandidate(item = {}) {
  const payload = item.payload ?? {};
  const sourceSpanId = item.source_span_id ?? item.sourceSpanId ?? null;
  const sourceSpanIds = item.source_span_ids ?? item.sourceSpanIds ?? (sourceSpanId ? [sourceSpanId] : []);
  return {
    id: item.id,
    name: payload.candidate_id ?? item.document_id ?? item.name ?? String(item.id ?? ''),
    type: payload.candidate_type ?? item.type ?? '',
    status: item.status ?? 'pending',
    confidence: payload.confidence ?? item.confidence ?? 0,
    conflictIds: item.conflict_ids ?? item.conflictIds ?? payload.conflict_ids ?? [],
    sourceSpanIds,
    documentId: item.document_id ?? item.documentId ?? null,
    updatedAt: item.updated_at ?? item.updatedAt ?? item.created_at ?? item.createdAt ?? null,
  };
}

export function mapReviewQueue(payload = {}) {
  const items = payload.items ?? payload.candidates ?? [];
  const conflicts = payload.conflicts ?? payload.conflict_items ?? [];
  return {
    items: items.map(mapReviewCandidate),
    total: payload.total ?? payload.total_found ?? items.length,
    filters: payload.filters ?? {},
    conflicts: conflicts.map((item) => ({
      id: item.id ?? item.conflict_id,
      claimA: item.claim_a ?? item.claimA ?? '',
      claimB: item.claim_b ?? item.claimB ?? '',
      conditionA: item.condition_a ?? item.conditionA ?? '',
      conditionB: item.condition_b ?? item.conditionB ?? '',
      sourceA: item.source_a ?? item.sourceA ?? null,
      sourceB: item.source_b ?? item.sourceB ?? null,
    })),
  };
}

export function serializeReviewQueueRequest(filters = {}) {
  return {
    status: filters.status ?? null,
    type: filters.type ?? null,
    from: filters.from ?? null,
    to: filters.to ?? null,
    limit: filters.limit ?? 50,
    offset: filters.offset ?? 0,
  };
}

export function buildReviewQueueQuery(filters = {}) {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(serializeReviewQueueRequest(filters))) {
    if (value != null && value !== '') {
      params.set(key, String(value));
    }
  }
  const query = params.toString();
  return query ? `?${query}` : '';
}

const REVIEW_DECISION_TO_API = {
  approved: 'approve',
  rejected: 'reject',
  deferred: 'defer',
  approve: 'approve',
  reject: 'reject',
  defer: 'defer',
};

export function serializeReviewDecision(payload = {}) {
  const itemId = payload.itemId ?? payload.item_id ?? payload.candidateId ?? payload.candidate_id;
  const decision = payload.decision ?? '';
  const sourceSpanIds = payload.sourceSpanIds ?? payload.source_span_ids ?? [];
  return {
    item_id: itemId,
    decision: REVIEW_DECISION_TO_API[decision] ?? decision,
    reason: payload.reason ?? payload.comment ?? payload.reasonCode ?? payload.reason_code ?? '',
    source_span_ids: sourceSpanIds,
  };
}

export function mapReviewDecisionResult(payload = {}) {
  return {
    candidateId: payload.item_id ?? payload.candidate_id ?? payload.candidateId ?? null,
    decision: payload.status ?? payload.decision ?? '',
    status: payload.status ?? 'accepted',
    auditEventId: payload.audit_event_id ?? payload.auditEventId ?? null,
  };
}

export function mapExportPayload(payload = {}) {
  return {
    exportJobId: payload.export_job_id ?? payload.exportJobId ?? null,
    queryRunId: payload.query_run_id ?? payload.queryRunId ?? null,
    format: payload.format ?? 'markdown',
    status: payload.status ?? 'completed',
    contentType: payload.content_type ?? payload.contentType ?? 'text/plain',
    content: payload.content ?? '',
    fileUrl: payload.file_url ?? payload.fileUrl ?? '',
    warnings: payload.warnings ?? [],
    generatedAt: payload.generated_at ?? payload.generatedAt ?? null,
  };
}

export function serializeExportRequest({ queryRunId, format = 'markdown' }) {
  return {
    query_run_id: queryRunId,
    format,
  };
}

export function mapDeleteDocumentResult(payload = {}) {
  return {
    documentId: payload.document_id ?? payload.documentId ?? null,
    status: payload.status ?? 'deleted',
    tombstoneId: payload.tombstone_id ?? payload.tombstoneId ?? null,
    warnings: payload.warnings ?? [],
  };
}

export function mapAdminUser(item = {}) {
  return {
    id: item.id,
    name: item.name ?? item.username ?? '',
    email: item.email ?? '',
    role: item.role ?? '',
    active: item.active ?? item.is_active ?? true,
  };
}

export function mapAdminPolicy(item = {}) {
  return {
    id: item.id ?? item.document_id,
    documentId: item.document_id ?? item.id,
    title: item.title ?? item.document_title ?? item.document ?? '',
    level: item.level ?? item.access_policy?.level ?? 'internal',
    exportAllowed: item.export_allowed ?? item.access_policy?.export_allowed ?? false,
    roles: item.roles ?? item.access_policy?.roles ?? [],
  };
}

export function serializeAdminUserPatch({ role, active }) {
  const body = {};
  if (role != null) {
    body.role = role;
  }
  if (active != null) {
    body.active = active;
    body.is_active = active;
  }
  return body;
}

export function serializeAdminPolicyPatch(accessPolicy = {}) {
  return {
    access_policy: {
      level: accessPolicy.level,
      export_allowed: accessPolicy.exportAllowed ?? accessPolicy.export_allowed,
      roles: accessPolicy.roles ?? [],
    },
  };
}

export function mapDictionaryVersion(item = {}) {
  return {
    id: item.id,
    version: item.version ?? '',
    status: item.status ?? 'inactive',
    packageSha256: item.package_sha256 ?? item.packageSha256 ?? '',
    filesCount: (item.files ?? []).length,
    createdAt: item.created_at ?? item.createdAt ?? null,
    activatedAt: item.activated_at ?? item.activatedAt ?? null,
  };
}
