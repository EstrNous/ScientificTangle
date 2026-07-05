import { apiGet } from './client.js';

const real = { real: true };

export function fetchSource(sourceSpanId) {
  return apiGet(`/source/${encodeURIComponent(sourceSpanId)}`, real);
}

export function mapSourcePayload(payload) {
  const span = payload?.source_span ?? {};
  const locked = payload?.access_denied === true || payload?.code === 'access_denied';
  return {
    id: span.id,
    title: payload?.document_title ?? span.document_id ?? '',
    page: span.page,
    section: span.table_block_id ? `table:${span.table_block_id}` : '',
    raw_text: span.text ?? '',
    highlight: span.text ?? '',
    highlightStart: span.highlight_start ?? span.highlightStart ?? null,
    highlightEnd: span.highlight_end ?? span.highlightEnd ?? null,
    tableRowId: span.table_row_id ?? span.tableRowId ?? null,
    tableRows: payload?.table_rows ?? span.table_rows ?? null,
    document_id: span.document_id,
    access_policy: payload?.access_policy,
    locked,
    accessDenied: locked,
  };
}
