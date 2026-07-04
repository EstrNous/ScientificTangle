import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { fetchSource, mapSourcePayload } from '../api/source.js';
import { mergeSourceSpan, resolveSourceRef } from '../api/mock/sourceCatalog.js';
import { useMock } from '../api/client.js';
import SourceDocumentModal from '../components/shared/SourceDocumentModal.jsx';

const SourceDocumentContext = createContext(null);

export function SourceDocumentProvider({ children }) {
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState(null);

  const openSource = useCallback(async (ref) => {
    if (typeof ref === 'object' && ref?.id && (ref?.pages || ref?.raw_text)) {
      setSource(mergeSourceSpan(ref));
      setOpen(true);
      return;
    }
    const refId = typeof ref === 'string' ? ref : ref?.source_span_id ?? ref?.id;
    if (!useMock && refId) {
      try {
        const payload = await fetchSource(refId);
        setSource(mapSourcePayload(payload));
        setOpen(true);
        return;
      } catch {
        return;
      }
    }
    const resolved = resolveSourceRef(ref);
    if (!resolved) return;
    setSource(mergeSourceSpan(resolved));
    setOpen(true);
  }, []);

  const closeSource = useCallback(() => {
    setOpen(false);
  }, []);

  const value = useMemo(
    () => ({
      openSource,
      closeSource,
    }),
    [openSource, closeSource],
  );

  return (
    <SourceDocumentContext.Provider value={value}>
      {children}
      <SourceDocumentModal open={open} source={source} onClose={closeSource} />
    </SourceDocumentContext.Provider>
  );
}

export function useSourceDocument() {
  const context = useContext(SourceDocumentContext);
  if (!context) {
    throw new Error('useSourceDocument must be used within SourceDocumentProvider');
  }
  return context;
}
