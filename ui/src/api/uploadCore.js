import { ensureAuth } from './auth.js';

const baseURL = import.meta.env.VITE_API_URL || '/api';

export async function uploadFiles(files, { kind = 'document' } = {}) {
  const token = await ensureAuth();
  const formData = new FormData();
  const path =
    kind === 'dictionary'
      ? `${baseURL}/dictionaries/upload`
      : `${baseURL}/documents/upload`;
  if (kind === 'dictionary') {
    if (!files.length) {
      throw new Error('upload_failed');
    }
    formData.append('package', files[0]);
  } else {
    files.forEach((file) => formData.append('files', file));
  }
  const response = await fetch(path, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  });
  if (!response.ok) {
    throw new Error('upload_failed');
  }
  return response.json();
}

export function resolveDocumentIdFromAuditEvent(event) {
  const details = event?.details ?? {};
  if (details.document_id) {
    return details.document_id;
  }
  if (Array.isArray(details.document_ids) && details.document_ids.length > 0) {
    return details.document_ids[0];
  }
  return null;
}

export function canDeleteAuditDocument(event) {
  return event?.action === 'ingestion_upload' && resolveDocumentIdFromAuditEvent(event) != null;
}

export function resolveUploadedDocuments(report) {
  const normalized = report?.normalized_documents ?? [];
  if (normalized.length > 0) {
    return normalized.map((document) => ({
      id: document.id,
      filename: document.title,
      kind:
        document.metadata?.upload_kind === 'dictionary' || document.source_type === 'json'
          ? 'dictionary'
          : 'document',
    }));
  }
  const sources = report?.sources ?? [];
  return sources
    .map((source) => ({
      id: source.document_id ?? source.sha256?.slice(0, 32),
      filename: source.original_filename,
      kind: source.content_type?.includes('json') ? 'dictionary' : 'document',
    }))
    .filter((item) => item.id);
}
