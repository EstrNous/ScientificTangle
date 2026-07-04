import { describe, expect, it } from 'vitest';
import { createEmptyEntity, deriveEntitiesFromReport } from './uploadEntities.js';

describe('deriveEntitiesFromReport', () => {
  it('builds document and candidate entities from report', () => {
    const entities = deriveEntitiesFromReport({
      sources: [
        {
          original_filename: 'nickel_report.pdf',
          sha256: 'a'.repeat(64),
        },
      ],
      normalized_documents: [
        {
          id: 'doc-1',
          title: 'Nickel recovery study',
          source_spans: [{ text: 'Nickel cathode efficiency improved' }],
        },
      ],
      candidates_count: 2,
    });

    expect(entities.some((entity) => entity.type === 'Document' && entity.name === 'nickel report')).toBe(true);
    expect(entities.some((entity) => entity.type === 'Material' && entity.name.includes('Nickel'))).toBe(true);
    expect(entities.filter((entity) => entity.status === 'candidate').length).toBeGreaterThanOrEqual(2);
  });
});

describe('createEmptyEntity', () => {
  it('returns editable draft entity', () => {
    const entity = createEmptyEntity();
    expect(entity.name).toBe('');
    expect(entity.type).toBe('Material');
    expect(entity.status).toBe('candidate');
  });
});
