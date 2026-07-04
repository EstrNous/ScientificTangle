import { useMemo } from 'react';
import { useSourceResolver } from './useSourceResolver.js';

export function useSourceRefRenderer({ sourceRef, source, children }) {
  const { mode, resolveSourceRef, sourceRefLabel } = useSourceResolver();

  return useMemo(() => {
    const resolved = mode === 'mock' ? resolveSourceRef(sourceRef) ?? resolveSourceRef(source) : null;
    const spanId =
      source?.source_span_id ??
      (typeof sourceRef === 'string' ? sourceRef : sourceRef?.id ?? sourceRef?.source_span_id);
    const label = children ?? sourceRefLabel(sourceRef ?? source) ?? sourceRef ?? source?.title;
    const openRef = mode === 'live' ? spanId : resolved;

    return {
      mode,
      label,
      spanId,
      resolved: resolved ?? (mode === 'live' ? resolveSourceRef(sourceRef) ?? resolveSourceRef(source) : null),
      openRef,
      isInteractive: mode === 'live' ? Boolean(spanId) : Boolean(resolved),
    };
  }, [children, mode, resolveSourceRef, source, sourceRef, sourceRefLabel]);
}
