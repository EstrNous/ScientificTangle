export function isSourceColumnName(name) {
  const normalized = String(name ?? '').trim().toLowerCase();
  return normalized === 'источник' || normalized === 'source' || normalized.includes('источник');
}

export function isDocumentColumnKey(key) {
  return String(key ?? '').toLowerCase() === 'document';
}
