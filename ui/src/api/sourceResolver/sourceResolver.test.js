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

  it('resolves offset highlights for review spans', () => {
    const resolved = mockAdapter.resolveSourceRef('span-101');
    const pages = mockAdapter.getDocumentViewPages(resolved);
    const cited = pages.find((page) => page.isCited);
    expect(cited?.highlightStart).toBe(11);
    expect(cited?.highlightEnd).toBe(16);
  });

  it('returns locked document for restricted span', async () => {
    const document = await mockAdapter.fetchSourceDocument('span-locked');
    expect(document?.accessDenied).toBe(true);
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

  it('labels object refs by document_title', () => {
    expect(liveAdapter.sourceRefLabel({ id: 'x', document_title: 'Nickel Report' })).toBe('Nickel Report');
  });
});

describe('sourceResolver facade', () => {
  afterEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
    vi.doUnmock('../../utils/uiFeatureFlags.js');
  });

  it('selects mock adapter when source live mode is disabled', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'true');
    vi.doMock('../../utils/uiFeatureFlags.js', () => ({
      isSourceLiveModeEnabled: () => false,
    }));
    const { getSourceMode, sourceRefLabel } = await import('./index.js');
    expect(getSourceMode()).toBe('mock');
    expect(sourceRefLabel('span-1')).toBe('nickel_report.pdf');
  });

  it('selects live adapter when source live mode is enabled', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    vi.doMock('../../utils/uiFeatureFlags.js', () => ({
      isSourceLiveModeEnabled: () => true,
    }));
    const { getSourceMode, sourceRefLabel } = await import('./index.js');
    expect(getSourceMode()).toBe('live');
    expect(sourceRefLabel('span-1')).toBe('span-1');
  });

  it('rejects mock adapter when mock bundle is disabled', async () => {
    vi.stubEnv('VITE_USE_MOCK', 'false');
    vi.doMock('../../utils/uiFeatureFlags.js', () => ({
      isSourceLiveModeEnabled: () => false,
    }));
    const { resolveSourceRef } = await import('./index.js');
    expect(() => resolveSourceRef('span-1')).toThrow('source_mock_unavailable');
  });
});
