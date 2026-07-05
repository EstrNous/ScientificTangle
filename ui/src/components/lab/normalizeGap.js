export function normalizeGap(gap, index = 0) {
  if (typeof gap === 'string') {
    const text = gap.trim();
    if (!text) return null;
    return {
      id: `gap-${index}`,
      title: text,
      description: text,
      constraints: [],
      related_cases: [],
      experts: [],
    };
  }
  if (!gap || typeof gap !== 'object') return null;
  const title = String(
    gap.title ?? gap.description ?? gap.expected_relation ?? `Gap ${index + 1}`,
  ).trim();
  const description = String(gap.description ?? gap.title ?? title).trim();
  if (!title && !description) return null;
  const constraints = Array.isArray(gap.constraints)
    ? gap.constraints.map((item) => String(item))
    : [];
  const entityIds = Array.isArray(gap.entity_ids)
    ? gap.entity_ids.map((item) => String(item))
    : [];
  const mergedConstraints = constraints.length ? constraints : entityIds;
  const priority = gap.priority ? String(gap.priority) : '';
  return {
    id: String(gap.id ?? gap.gap_id ?? `gap-${index}`),
    title,
    description,
    constraints:
      priority && !mergedConstraints.includes(priority)
        ? [...mergedConstraints, priority]
        : mergedConstraints,
    related_cases: Array.isArray(gap.related_cases)
      ? gap.related_cases.filter((item) => item && typeof item === 'object')
      : [],
    experts: Array.isArray(gap.experts) ? gap.experts.map((item) => String(item)) : [],
  };
}
