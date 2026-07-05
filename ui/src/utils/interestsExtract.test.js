import { describe, expect, it } from 'vitest';
import { extractInterests } from './interestsExtract.js';

describe('extractInterests', () => {
  it('extracts domain terms from text', () => {
    const interests = extractInterests('Флотация никель, отечественный опыт');
    const labels = interests.map((item) => item.label);
    expect(labels).toContain('materials');
    expect(labels).toContain('processes');
    expect(labels).toContain('geography');
  });

  it('extracts chemical formulas', () => {
    const interests = extractInterests('Соединение NiSO4 в растворе');
    const formula = interests.find((item) => item.label.startsWith('substance:'));
    expect(formula?.source_terms).toContain('NiSO4');
  });
});
