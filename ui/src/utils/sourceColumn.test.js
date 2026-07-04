import { describe, expect, it } from 'vitest';
import { isDocumentColumnKey, isSourceColumnName } from './sourceColumn.js';

describe('sourceColumn', () => {
  it('detects localized source column names', () => {
    expect(isSourceColumnName('Источник')).toBe(true);
    expect(isSourceColumnName('source')).toBe(true);
    expect(isSourceColumnName('Колонка источника')).toBe(true);
    expect(isSourceColumnName('material')).toBe(false);
  });

  it('detects document column key', () => {
    expect(isDocumentColumnKey('document')).toBe(true);
    expect(isDocumentColumnKey('Document')).toBe(true);
    expect(isDocumentColumnKey('source')).toBe(false);
  });
});
