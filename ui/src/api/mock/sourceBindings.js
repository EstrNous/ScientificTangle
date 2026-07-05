import { getSourceById, resolveSourceRef, SOURCE_ENTRIES } from './sourceCatalog.js';

const ALL_SPAN_IDS = Object.keys(SOURCE_ENTRIES);

const ROW_SOURCES = {
  Никель: ['span-1', 'span-3', 'span-4', 'span-7'],
  Медь: ['span-5', 'span-6', 'span-8'],
  'Шахтная вода': ['span-2', 'span-9'],
  ВТ6: ['span-5', 'span-8'],
  Шлак: ['span-6', 'span-8'],
  'EXP-2024-017': ['span-1', 'span-4'],
  'EXP-2023-031': ['span-3', 'span-7'],
  'EXP-2022-008': ['span-2', 'span-9'],
  'EXP-2021-044': ['span-4', 'span-10'],
  'EXP-2020-012': ['span-5', 'span-6'],
  'Иванов А.С.': ['span-4', 'span-7'],
  'Smith J.': ['span-1', 'span-3'],
  'Новикова Е.П.': ['span-2', 'span-9'],
};

const COL_SOURCES = {
  Электроэкстракция: ['span-1', 'span-3', 'span-4'],
  Обессоливание: ['span-2', 'span-9'],
  Флотация: ['span-6', 'span-8'],
  'Кучное выщеливание': ['span-10', 'span-7'],
  'Лаб. физико-химии': ['span-1', 'span-4'],
  'Гидрометаллургическая лаборатория': ['span-3', 'span-7'],
  'Лаб. аналитической химии': ['span-2', 'span-9'],
  'Пилотная установка HL': ['span-10', 'span-4'],
  'nickel_report.pdf': ['span-1'],
  'water_desalination.docx': ['span-2'],
  'J. Hydrometallurgy, 2024': ['span-3'],
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

export function getMatrixCellSources(row, col, count, rowType = '', colType = '') {
  if (!count) return [];

  if (colType === 'Document') {
    const resolved = resolveSourceRef(col);
    return resolved ? [resolved.id] : limitRefs([col], 1);
  }
  if (rowType === 'Document') {
    const resolved = resolveSourceRef(row);
    return resolved ? [resolved.id] : limitRefs([row], 1);
  }

  const merged = uniqueRefs([...(ROW_SOURCES[row] ?? []), ...(COL_SOURCES[col] ?? [])]);
  if (merged.length) return limitRefs(merged, count);

  return limitRefs(ALL_SPAN_IDS, Math.min(count, 4));
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
