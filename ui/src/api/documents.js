import { apiDelete, apiOptions } from './client.js';
import { mapApiError } from './errors.js';
import { mapDeleteDocumentResult } from './mappers/productApi.js';

export async function deleteDocument(documentId) {
  try {
    const payload = await apiDelete(`/documents/${encodeURIComponent(documentId)}`, apiOptions());
    return mapDeleteDocumentResult(payload ?? { document_id: documentId, status: 'deleted' });
  } catch (error) {
    throw new Error(mapApiError(error, 'delete_failed'));
  }
}

export { mapDeleteDocumentResult } from './mappers/productApi.js';
