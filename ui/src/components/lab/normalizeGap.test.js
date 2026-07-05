import { describe, expect, it } from 'vitest';
import { normalizeGap } from './normalizeGap.js';

describe('normalizeGap', () => {
  it('maps string gaps to view model', () => {
    const gap = normalizeGap('Ni flotation gap', 0);
    expect(gap).toEqual({
      id: 'gap-0',
      title: 'Ni flotation gap',
      description: 'Ni flotation gap',
      constraints: [],
      related_cases: [],
      experts: [],
    });
  });

  it('maps knowledge gap dto to view model', () => {
    const gap = normalizeGap(
      {
        gap_id: 'g1',
        description: 'Отсутствует измерение выхода',
        expected_relation: 'PRODUCES_OUTPUT',
        entity_ids: ['proc-1', 'mat-1'],
        priority: 'medium',
      },
      1,
    );
    expect(gap.id).toBe('g1');
    expect(gap.title).toContain('Отсутствует');
    expect(gap.constraints).toEqual(['proc-1', 'mat-1', 'medium']);
  });
});
