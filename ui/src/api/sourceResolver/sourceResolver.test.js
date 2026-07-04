import { afterEach, describe, expect, it, vi } from 'vitest';
import * as mockAdapter from './mockAdapter.js';
import * as liveAdapter from './liveAdapter.js';

describe('sourceResolver mockAdapter', () => {
  it('resolves catalog span by id', () => {
    const resolved = mockAdapter.resolveSourceRef('span-1');
    expect(resolved?.id).toBe('span-1');
    expect(resolved?.title).toBe('nickel_report.pdf');
  });

  it('labels mock refs via catalog title', () => {
    expect(mockAdapter.sourceRefLabel('span-1')).toBe('nickel_report.pdf');
  });

  it('collects evidence row sources from document columns', () => {
    const sources = mockAdapter.getEvidenceRowSources(
      ['2–4 м/ч', 'nickel_report.pdf'],
      ['Скорость', 'Документ'],
    );
    expect(sources).toContain('span-1');
  });
});

describe('sourceResolver liveAdapter', () => {
  it('exposes span id from string ref', () => {
    const resolved = liveAdapter.resolveSourceRef('span-live-42');
    expect(resolved?.id).toBe('span-live-42');
  });

  it('labels object refs by title', () => {
    expect(liveAdapter.sourceRefLabel({ id: 'x', title: 'Report A' })).toBe('Report A');
  });
});

describe('sourceResolver facade', () => {
  afterEach(() => {
    vi.resetModules();
    vi.doUnmock('../client.js');
  });

  it('selects mock adapter when useMock is true', async () => {
    vi.doMock('../client.js', () => ({ useMock: true }));
    const { getSourceMode, sourceRefLabel } = await import('./index.js');
    expect(getSourceMode()).toBe('mock');
    expect(sourceRefLabel('span-1')).toBe('nickel_report.pdf');
  });

  it('selects live adapter when useMock is false', async () => {
    vi.doMock('../client.js', () => ({ useMock: false }));
    const { getSourceMode, sourceRefLabel } = await import('./index.js');
    expect(getSourceMode()).toBe('live');
    expect(sourceRefLabel('span-1')).toBe('span-1');
  });
});
