import { isSourceLiveModeEnabled } from '../../utils/uiFeatureFlags.js';
import { resolveUseMock } from '../../utils/runtimeMode.js';
import * as liveAdapter from './liveAdapter.js';

let mockAdapterModule = null;
let mockAdapterPromise = null;

export async function ensureMockSourceResolver() {
  if (import.meta.env.PROD || !resolveUseMock()) {
    return null;
  }
  if (mockAdapterModule) {
    return mockAdapterModule;
  }
  if (!mockAdapterPromise) {
    mockAdapterPromise = import('./mockAdapter.js').then((module) => {
      mockAdapterModule = module;
      return module;
    });
  }
  return mockAdapterPromise;
}

if (!import.meta.env.PROD && import.meta.env.VITE_USE_MOCK === 'true') {
  void ensureMockSourceResolver();
}

function getAdapter() {
  if (isSourceLiveModeEnabled()) {
    return liveAdapter;
  }
  if (import.meta.env.PROD || !resolveUseMock()) {
    throw new Error('source_mock_unavailable');
  }
  if (!mockAdapterModule) {
    throw new Error('source_mock_adapter_not_ready');
  }
  return mockAdapterModule;
}

export function getSourceMode() {
  return isSourceLiveModeEnabled() ? 'live' : 'mock';
}

export function resolveSourceRef(ref) {
  return getAdapter().resolveSourceRef(ref);
}

export function mergeSourceSpan(span) {
  return getAdapter().mergeSourceSpan(span);
}

export function sourceRefLabel(ref) {
  return getAdapter().sourceRefLabel(ref);
}

export function getEvidenceRowSources(row, columns) {
  return getAdapter().getEvidenceRowSources(row, columns);
}

export function getCombinationRowSources(row, columns, isDocumentColumnKey) {
  return getAdapter().getCombinationRowSources(row, columns, isDocumentColumnKey);
}

export function getMatrixCellSources(row, col, count, rowType, colType) {
  return getAdapter().getMatrixCellSources(row, col, count, rowType, colType);
}

export function getDocumentViewPages(entry) {
  return getAdapter().getDocumentViewPages(entry);
}

export function getFullDocumentPages(entry) {
  return getAdapter().getFullDocumentPages(entry);
}

export async function fetchSourceDocument(ref) {
  if (!isSourceLiveModeEnabled() && resolveUseMock()) {
    await ensureMockSourceResolver();
  }
  return getAdapter().fetchSourceDocument(ref);
}
