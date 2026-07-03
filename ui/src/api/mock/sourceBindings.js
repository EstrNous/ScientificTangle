import { getSourceById, resolveSourceRef, SOURCE_ENTRIES } from './sourceCatalog.js';

const ALL_SPAN_IDS = Object.keys(SOURCE_ENTRIES);

const DIRECTION_SOURCES = {
  hydro: ['span-1', 'span-2', 'span-3', 'span-4', 'span-7'],
  pyro: ['span-5', 'span-6', 'span-8'],
  eco: ['span-2', 'span-9', 'span-10'],
  waste: ['span-6', 'span-8', 'span-10'],
  water: ['span-2', 'span-9'],
  ew: ['span-1', 'span-3', 'span-4'],
  gas: ['span-10', 'span-7'],
};

const METRIC_SOURCES = {
  documents: ALL_SPAN_IDS,
  claims: ['span-1', 'span-2', 'span-3', 'span-4', 'span-5', 'span-6'],
  verified_claims: ['span-1', 'span-2', 'span-3', 'span-4'],
  candidates: ['span-7', 'span-8', 'span-9'],
  gaps: ['span-10'],
  conflicts: ['span-1', 'span-4', 'span-3'],
};

const QUESTION_SOURCES = {
  'official-001': ['span-2', 'span-9'],
  'official-002': ['span-1', 'span-3', 'span-4'],
  'official-003': ['span-5', 'span-6', 'span-8'],
  'official-004': ['span-2', 'span-9', 'span-10'],
  'official-005': ['span-4', 'span-7', 'span-10'],
};

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

export function getDirectionSources(directionId, documentCount) {
  const pool = DIRECTION_SOURCES[directionId] ?? ALL_SPAN_IDS;
  const limit = Math.min(documentCount ?? pool.length, 8, pool.length);
  return limitRefs(pool, Math.max(limit, 1));
}

export function getMetricSources(metricKey, total) {
  const pool = METRIC_SOURCES[metricKey] ?? ALL_SPAN_IDS;
  const limit = Math.min(total ?? pool.length, 6, pool.length);
  return limitRefs(pool, Math.max(limit, 1));
}

export function getQuestionSources(questionId, actualSources) {
  const pool = QUESTION_SOURCES[questionId] ?? ALL_SPAN_IDS;
  return limitRefs(pool, Math.min(actualSources ?? pool.length, pool.length));
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
