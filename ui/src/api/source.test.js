import { describe, expect, it } from 'vitest';
import { mapSourcePayload } from './source.js';

describe('mapSourcePayload', () => {
  it('maps highlight offsets and table row metadata', () => {
    const mapped = mapSourcePayload({
      document_title: 'lab.pdf',
      source_span: {
        id: 'span-101',
        page: 3,
        text: 'Содержание NiSO4 в растворе',
        highlight_start: 11,
        highlight_end: 16,
        table_row_id: 'row-3',
      },
      table_rows: [{ id: 'row-3', cells: ['B', '2–4 м/ч'] }],
    });
    expect(mapped.highlightStart).toBe(11);
    expect(mapped.highlightEnd).toBe(16);
    expect(mapped.tableRowId).toBe('row-3');
    expect(mapped.tableRows).toHaveLength(1);
  });

  it('marks access denied payloads as locked', () => {
    const mapped = mapSourcePayload({
      code: 'access_denied',
      source_span: { id: 'span-locked' },
    });
    expect(mapped.locked).toBe(true);
    expect(mapped.accessDenied).toBe(true);
  });
});
