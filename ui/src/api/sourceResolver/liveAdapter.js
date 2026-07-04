import { fetchSource, mapSourcePayload } from '../source.js';

function refId(ref) {
  if (!ref) return null;
  if (typeof ref === 'string') return ref;
  return ref.source_span_id ?? ref.id ?? ref.source_ref ?? null;
}

export function resolveSourceRef(ref) {
  if (!ref) return null;
  if (typeof ref === 'object' && (ref.pages || ref.raw_text || ref.title)) {
    return ref;
  }
  const id = refId(ref);
  if (!id) return null;
  if (typeof ref === 'object') {
    return {
      id,
      title: ref.title ?? ref.document_id ?? ref.file_name ?? id,
      page: ref.page,
      raw_text: ref.text ?? ref.raw_text ?? '',
      highlight: ref.text ?? ref.highlight ?? null,
      document_id: ref.document_id,
    };
  }
  return { id, title: id };
}

export function mergeSourceSpan(span) {
  return span;
}

export function sourceRefLabel(ref) {
  if (!ref) return '';
  if (typeof ref === 'object') {
    return ref.title ?? ref.file_name ?? ref.document_id ?? ref.id ?? '';
  }
  return String(ref);
}

export function getEvidenceRowSources(row, columns) {
  const refs = columns
    .map((_, index) => {
      const cell = row[index];
      if (!cell) return null;
      return refId(cell);
    })
    .filter(Boolean);
  return [...new Set(refs)];
}

export function getCombinationRowSources(row, columns, isDocumentColumnKey) {
  const refs = columns
    .filter((column) => isDocumentColumnKey(column.key))
    .map((column) => refId(row[column.key]))
    .filter(Boolean);
  return [...new Set(refs)];
}

export function getMatrixCellSources() {
  return [];
}

export async function fetchSourceDocument(ref) {
  const id = refId(ref);
  if (!id) return null;
  const payload = await fetchSource(id);
  return mapSourcePayload(payload);
}

export function getDocumentViewPages(entry) {
  if (!entry) return [];
  const page = entry.page ?? 1;
  return [
    {
      page,
      raw_text: entry.raw_text ?? '',
      highlight: entry.highlight ?? null,
      section: entry.section ?? null,
      isCited: true,
    },
  ];
}

export function getFullDocumentPages(entry) {
  return getDocumentViewPages(entry);
}
