import { getSourceById, resolveSourceRef, SOURCE_ENTRIES } from './sourceCatalog.js';

const ALL_SPAN_IDS = Object.keys(SOURCE_ENTRIES);

function hashKey(value) {
  let hash = 0;
  const text = String(value);
  for (let i = 0; i < text.length; i += 1) {
    hash = (hash * 31 + text.charCodeAt(i)) >>> 0;
  }
  return hash;
}

function uniqueRefs(refs) {
  return [...new Set(refs.filter(Boolean))];
}

function limitRefs(refs, count) {
  if (!count || count <= 0) return [];
  const unique = uniqueRefs(refs);
  if (!unique.length) return [];
  if (unique.length >= count) return unique.slice(0, count);
  const result = [...unique];
  let cursor = hashKey(unique.join('|')) % ALL_SPAN_IDS.length;
  while (result.length < count && result.length < ALL_SPAN_IDS.length) {
    const candidate = ALL_SPAN_IDS[cursor % ALL_SPAN_IDS.length];
    if (!result.includes(candidate)) result.push(candidate);
    cursor += 1;
  }
  return result;
}

export function getEvidenceRowSources(row, columns) {
  const refs = columns
    .map((column, index) => {
      const cell = row[index];
      if (!cell) return null;
      const resolved = resolveSourceRef(cell);
      return resolved?.id ?? null;
    })
    .filter(Boolean);
  if (refs.length) return uniqueRefs(refs);
  return limitRefs(ALL_SPAN_IDS, 2);
}

export function getCombinationRowSources(row, columns, isDocumentColumnKey) {
  const refs = columns
    .filter((column) => isDocumentColumnKey(column.key))
    .map((column) => {
      const value = row[column.key];
      if (!value) return null;
      const resolved = resolveSourceRef(value);
      return resolved?.id ?? null;
    })
    .filter(Boolean);
  return uniqueRefs(refs);
}

export function sourceRefLabel(ref) {
  const entry = typeof ref === 'string' ? getSourceById(ref) : ref;
  return entry?.title ?? entry?.file_name ?? String(ref);
}
