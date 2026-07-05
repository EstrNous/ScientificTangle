import { afterEach, describe, expect, it, vi } from 'vitest';
import { buildSearchQuery } from '../api/search.js';
import { resolveUploadTaskStages } from '../utils/uploadTaskStages.js';
import { collectCandidateConflicts, indexReviewConflicts } from '../utils/reviewConflicts.js';

describe('buildSearchQuery', () => {
  it('includes geo, numeric, year and pagination params', () => {
    const query = buildSearchQuery({
      question: 'nickel',
      geo: ['Russia'],
      sourceTypes: ['table'],
      yearFrom: 2020,
      yearTo: 2024,
      numericValue: 82,
      numericUnit: '%',
      limit: 40,
      offset: 20,
    });
    const params = new URLSearchParams(query);
    expect(params.get('question')).toBe('nickel');
    expect(params.get('geo')).toBe('Russia');
    expect(params.get('source_type')).toBe('table');
    expect(params.get('year_from')).toBe('2020');
    expect(params.get('year_to')).toBe('2024');
    expect(params.get('numeric_value')).toBe('82');
    expect(params.get('numeric_unit')).toBe('%');
    expect(params.get('limit')).toBe('40');
    expect(params.get('offset')).toBe('20');
  });
});

describe('resolveUploadTaskStages', () => {
  const t = (key) => key;

  it('uses backend stages when present', () => {
    const stages = resolveUploadTaskStages(
      {
        stages: [{ id: 'parse', status: 'completed' }],
      },
      t,
    );
    expect(stages).toHaveLength(1);
    expect(stages[0].id).toBe('parse');
    expect(stages[0].status).toBe('done');
  });

  it('returns empty array for null task', () => {
    expect(resolveUploadTaskStages(null, t)).toEqual([]);
  });

  it('derives document stages from task status', () => {
    const stages = resolveUploadTaskStages(
      {
        status: 'processing',
        report: { documents_count: 1, source_spans_count: 2 },
      },
      t,
    );
    expect(stages.some((stage) => stage.id === 'extract' && stage.status === 'active')).toBe(true);
  });
});

describe('reviewConflicts', () => {
  it('indexes conflicts and resolves candidate links', () => {
    const conflictsById = indexReviewConflicts([
      {
        id: 'conflict-1',
        claim_a: 'A',
        claim_b: 'B',
        source_a: 'span-1',
        source_b: 'span-2',
      },
    ]);
    const selected = collectCandidateConflicts({ conflictIds: ['conflict-1'] }, conflictsById);
    expect(selected).toHaveLength(1);
    expect(selected[0].sourceA).toBe('span-1');
  });
});

describe('answerLifecycleFixtures', () => {
  it('builds retrieval steps without mock api imports', async () => {
    const fixtures = await import('../utils/simulation/answerLifecycleFixtures.js');
    const steps = fixtures.buildRetrievalSteps([], (key) => key);
    expect(steps.length).toBeGreaterThan(2);
    const reply = fixtures.buildSimulatedAssistantReply('test', []);
    expect(reply.content).toContain('test');
  });
});

describe('uiFeatureFlags role switcher', () => {
  afterEach(() => {
    vi.unstubAllEnvs();
    vi.resetModules();
  });

  it('enables role switcher in mock mode', async () => {
    vi.doMock('./runtimeMode.js', () => ({
      useMock: true,
      resolveUseMock: () => true,
    }));
    vi.resetModules();
    const flags = await import('../utils/uiFeatureFlags.js');
    expect(flags.isDevRoleSwitcherEnabled()).toBe(true);
    expect(flags.isProductionAuthMode()).toBe(false);
  });
});
