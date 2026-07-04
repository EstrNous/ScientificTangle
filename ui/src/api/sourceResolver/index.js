import { isSourceLiveModeEnabled } from '../../utils/uiFeatureFlags.js';
import * as liveAdapter from './liveAdapter.js';

const mockSourcesEnabled = import.meta.env.VITE_USE_MOCK === 'true';

const mockAdapter = mockSourcesEnabled ? await import('./mockAdapter.js') : null;

function getAdapter() {
  if (isSourceLiveModeEnabled()) {
    return liveAdapter;
  }
  if (!mockSourcesEnabled || !mockAdapter) {
    throw new Error('source_mock_unavailable');
  }
  return mockAdapter;
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
  return getAdapter().fetchSourceDocument(ref);
}
