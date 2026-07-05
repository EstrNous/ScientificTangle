const ENTITY_PATTERN = /\b[A-ZА-ЯЁ][a-zа-яё]{2,}(?:[-\s][a-zа-яё]{2,})?\b/g;

function uniqueId(prefix) {
  if (typeof crypto?.randomUUID === 'function') {
    return `${prefix}-${crypto.randomUUID()}`;
  }
  if (typeof crypto?.getRandomValues === 'function') {
    const bytes = new Uint8Array(16);
    crypto.getRandomValues(bytes);
    const hex = [...bytes].map((byte) => byte.toString(16).padStart(2, '0')).join('');
    return `${prefix}-${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

function titleFromFilename(filename) {
  if (!filename) return '';
  return filename.replace(/\.[^.]+$/, '').replace(/[_-]+/g, ' ').trim();
}

function collectTermsFromText(text, limit = 12) {
  if (!text) return [];
  const matches = text.match(ENTITY_PATTERN) ?? [];
  const seen = new Set();
  const terms = [];
  for (const match of matches) {
    const key = match.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    terms.push(match);
    if (terms.length >= limit) break;
  }
  return terms;
}

export function deriveEntitiesFromReport(report) {
  if (!report) return [];

  const entities = [];
  const sources = report.sources ?? [];

  sources.forEach((source, index) => {
    const name = titleFromFilename(source.original_filename);
    if (!name) return;
    entities.push({
      id: uniqueId(`doc-${index}`),
      name,
      type: 'Document',
      status: 'verified',
      confidence: 1,
    });
  });

  const documents = report.normalized_documents ?? [];
  documents.forEach((document) => {
    const terms = new Set();
    collectTermsFromText(document.title, 4).forEach((term) => terms.add(term));
    (document.source_spans ?? []).slice(0, 8).forEach((span) => {
      collectTermsFromText(span.text, 6).forEach((term) => terms.add(term));
    });
    terms.forEach((term) => {
      entities.push({
        id: uniqueId('entity'),
        name: term,
        type: 'Material',
        status: 'candidate',
        confidence: 0.65,
      });
    });
  });

  const existingCandidates = entities.filter((entity) => entity.status === 'candidate').length;
  const targetCandidates = report.candidates_count ?? 0;
  for (let index = existingCandidates; index < targetCandidates; index += 1) {
    entities.push({
      id: uniqueId('candidate'),
      name: `Entity ${index + 1}`,
      type: 'Material',
      status: 'candidate',
      confidence: 0.5,
    });
  }

  const seen = new Set();
  return entities.filter((entity) => {
    const key = `${entity.type}:${entity.name.toLowerCase()}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

export function createEmptyEntity() {
  return {
    id: uniqueId('new'),
    name: '',
    type: 'Material',
    status: 'candidate',
    confidence: 0.5,
  };
}
