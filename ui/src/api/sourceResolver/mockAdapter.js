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
  if (resolved.access_denied || resolved.locked) {
    return {
      id: resolved.id,
      title: resolved.title,
      locked: true,
      accessDenied: true,
    };
  }
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
