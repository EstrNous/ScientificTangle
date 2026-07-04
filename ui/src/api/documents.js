import { apiGet } from './client.js';
import { mapDocumentCatalog } from './mappers/productApi.js';

export async function fetchDocumentCatalog(params = {}) {
  const search = new URLSearchParams();
  if (params.status) {
    search.set('status', params.status);
  }
  if (params.filter) {
    search.set('filter', params.filter);
  }
  if (params.limit != null) {
    search.set('limit', String(params.limit));
  }
  if (params.offset != null) {
    search.set('offset', String(params.offset));
  }
  const query = search.toString();
  const payload = await apiGet(`/documents${query ? `?${query}` : ''}`);
  return mapDocumentCatalog(payload);
}
