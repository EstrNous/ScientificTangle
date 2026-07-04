export function mapReviewConflict(item = {}) {
  return {
    id: item.id ?? item.conflict_id ?? '',
    claimA: item.claim_a ?? item.claimA ?? '',
    claimB: item.claim_b ?? item.claimB ?? '',
    conditionA: item.condition_a ?? item.conditionA ?? '',
    conditionB: item.condition_b ?? item.conditionB ?? '',
    sourceA: item.source_a ?? item.sourceA ?? null,
    sourceB: item.source_b ?? item.sourceB ?? null,
  };
}

export function indexReviewConflicts(conflicts = []) {
  const map = new Map();
  conflicts.forEach((item) => {
    const mapped = mapReviewConflict(item);
    if (mapped.id) {
      map.set(mapped.id, mapped);
    }
  });
  return map;
}

export function collectCandidateConflicts(candidate, conflictsById) {
  if (!candidate?.conflictIds?.length) return [];
  return candidate.conflictIds.map((id) => conflictsById.get(id)).filter(Boolean);
}
