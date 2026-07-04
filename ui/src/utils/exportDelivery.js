function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function extensionForFormat(format, contentType = '') {
  if (format === 'json' || contentType.includes('json')) return 'json';
  if (format === 'jsonld' || contentType.includes('ld+json')) return 'jsonld';
  if (format === 'pdf' || contentType.includes('pdf')) return 'pdf';
  return 'md';
}

export function isRemoteExportUrl(fileUrl) {
  if (!fileUrl || typeof fileUrl !== 'string') return false;
  return /^https?:\/\//i.test(fileUrl);
}

export function isInlineExportUrl(fileUrl) {
  if (!fileUrl || typeof fileUrl !== 'string') return false;
  return fileUrl.startsWith('inline://');
}

export function downloadExportPayload(exportResult, { fallbackName = 'export' } = {}) {
  const format = exportResult.format ?? 'markdown';
  const contentType = exportResult.contentType ?? '';
  const extension = extensionForFormat(format, contentType);
  const filename = `${fallbackName}.${extension}`;

  if (isRemoteExportUrl(exportResult.fileUrl)) {
    window.open(exportResult.fileUrl, '_blank', 'noopener,noreferrer');
    return;
  }

  const rawContent = exportResult.content;
  if (rawContent == null || rawContent === '') {
    throw new Error('export_empty');
  }

  const body =
    typeof rawContent === 'string' ? rawContent : JSON.stringify(rawContent, null, 2);
  const mime =
    contentType ||
    (format === 'json' || format === 'jsonld'
      ? 'application/json;charset=utf-8'
      : 'text/markdown;charset=utf-8');
  triggerDownload(new Blob([body], { type: mime }), filename);
}

export const EXPORT_POLL_INTERVAL_MS = 1500;
export const EXPORT_POLL_MAX_ATTEMPTS = 20;

export function isExportProcessing(status) {
  const normalized = String(status ?? '').toLowerCase();
  return normalized === 'processing' || normalized === 'pending' || normalized === 'queued';
}

export async function wait(ms) {
  await new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}
