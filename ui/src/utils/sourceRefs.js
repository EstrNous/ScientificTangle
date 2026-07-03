function normalizeRefs(raw) {
  return raw
    .map((entry) => {
      if (typeof entry === 'string') return entry;
      return entry?.id ?? entry?.document_id ?? null;
    })
    .filter(Boolean);
}

export function collectSourceRefs(item, limit) {
  const raw = Array.isArray(item)
    ? item
    : (item?.sources ?? item?.source_refs ?? item?.source_span_ids ?? []);
  const refs = normalizeRefs(raw);

  if (!refs.length) return [];
  if (limit && limit > 0) return refs.slice(0, limit);
  return refs;
}
