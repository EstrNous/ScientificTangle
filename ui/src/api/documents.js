import { apiDelete, apiGet, apiOptions } from './client.js';
import { mapApiError } from './errors.js';
import { mapDeleteDocumentResult, mapDocumentCatalog, mapDocumentCatalogItem } from './mappers/productApi.js';

export async function deleteDocument(documentId) {
  try {
    const payload = await apiDelete(`/documents/${encodeURIComponent(documentId)}`, apiOptions());
    return mapDeleteDocumentResult(payload ?? { document_id: documentId, status: 'deleted' });
  } catch (error) {
    throw new Error(mapApiError(error, 'delete_failed'));
  }
}

export async function fetchDocument(documentId) {
  try {
    const payload = await apiGet(`/documents/${encodeURIComponent(documentId)}`, apiOptions());
    return mapDocumentCatalogItem(payload);
  } catch (error) {
    throw new Error(mapApiError(error, 'document_load_failed'));
  }
}

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

export { mapDeleteDocumentResult } from './mappers/productApi.js';
