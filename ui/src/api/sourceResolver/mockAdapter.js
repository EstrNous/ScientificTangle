import {
  getDocumentViewPages,
  getFullDocumentPages,
  mergeSourceSpan,
  resolveSourceRef,
} from '../mock/sourceCatalog.js';
import {
  getCombinationRowSources,
  getEvidenceRowSources,
  getMatrixCellSources,
  sourceRefLabel,
} from '../mock/sourceBindings.js';

async function fetchSourceDocument(ref) {
  const resolved = resolveSourceRef(ref);
  if (!resolved) return null;
  return mergeSourceSpan(resolved);
}

export {
  fetchSourceDocument,
  getCombinationRowSources,
  getDocumentViewPages,
  getEvidenceRowSources,
  getFullDocumentPages,
  getMatrixCellSources,
  mergeSourceSpan,
  resolveSourceRef,
  sourceRefLabel,
};
