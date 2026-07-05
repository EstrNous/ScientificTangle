import { ensureAuth } from './auth.js';

const baseURL = import.meta.env.VITE_API_URL || '/api';

function createUploadError(code = 'upload_failed') {
  const error = new Error(code);
  error.code = code;
  return error;
}

export async function uploadFiles(files, { kind = 'document' } = {}) {
  if (!files.length) {
    throw createUploadError();
  }
  const token = await ensureAuth();
  const formData = new FormData();
  const path =
    kind === 'dictionary'
      ? `${baseURL}/dictionaries/upload`
      : `${baseURL}/documents/upload`;
  if (kind === 'dictionary') {
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
    throw createUploadError();
  }
  return response.json();
}

export async function waitForIngestionTask(
  taskId,
  { timeoutMs = 900000, intervalMs = 1500 } = {},
) {
  const token = await ensureAuth();
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const response = await fetch(`${baseURL}/tasks/${taskId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) {
      throw createUploadError();
    }
    const payload = await response.json();
    if (payload.status === 'completed') {
      return payload;
    }
    if (payload.status === 'failed') {
      throw createUploadError();
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw createUploadError();
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

const DELETABLE_UPLOAD_ACTIONS = new Set(['ingestion_upload', 'document_uploaded']);

export function canDeleteAuditDocument(event) {
  return DELETABLE_UPLOAD_ACTIONS.has(event?.action) && resolveDocumentIdFromAuditEvent(event) != null;
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
