import { useMemo } from 'react';
import { useSourceResolver } from './useSourceResolver.js';

export function useSourceRefRenderer({ sourceRef, source, children }) {
  const { mode, resolveSourceRef, sourceRefLabel } = useSourceResolver();

  return useMemo(() => {
    const resolved = resolveSourceRef(sourceRef) ?? resolveSourceRef(source);
    const spanId =
      source?.source_span_id ??
      resolved?.id ??
      (typeof sourceRef === 'string' ? sourceRef : sourceRef?.id ?? sourceRef?.source_span_id ?? null);
    const label =
      children ?? sourceRefLabel(sourceRef ?? source) ?? resolved?.title ?? spanId ?? '';
    const openRef = mode === 'live' ? spanId : resolved;

    return {
      mode,
      label,
      spanId,
      resolved,
      openRef,
      isInteractive: mode === 'live' ? Boolean(spanId) : Boolean(resolved),
    };
  }, [children, mode, resolveSourceRef, source, sourceRef, sourceRefLabel]);
}
