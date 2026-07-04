import { apiGet } from './client.js';

const real = { real: true };

export function fetchSource(sourceSpanId) {
  return apiGet(`/source/${encodeURIComponent(sourceSpanId)}`, real);
}

export function mapSourcePayload(payload) {
  const span = payload?.source_span ?? {};
  return {
    id: span.id,
    title: payload?.document_title ?? span.document_id ?? '',
    page: span.page,
    section: span.table_block_id ? `table:${span.table_block_id}` : '',
    raw_text: span.text ?? '',
    highlight: span.text ?? '',
    document_id: span.document_id,
    access_policy: payload?.access_policy,
  };
}
