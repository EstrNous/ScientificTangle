import { useMemo } from 'react';
import {
  fetchSourceDocument,
  getEvidenceRowSources,
  getSourceMode,
  mergeSourceSpan,
  resolveSourceRef,
  sourceRefLabel,
} from '../api/sourceResolver/index.js';

export function useSourceResolver() {
  return useMemo(
    () => ({
      mode: getSourceMode(),
      resolveSourceRef,
      mergeSourceSpan,
      sourceRefLabel,
      getEvidenceRowSources,
      fetchSourceDocument,
    }),
    [],
  );
}
