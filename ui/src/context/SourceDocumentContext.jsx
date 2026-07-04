import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { fetchSourceDocument, mergeSourceSpan } from '../api/sourceResolver/index.js';
import SourceDocumentModal from '../components/shared/SourceDocumentModal.jsx';

const SourceDocumentContext = createContext(null);

function isAccessDeniedDocument(document) {
  return Boolean(document?.accessDenied || document?.locked);
}

export function SourceDocumentProvider({ children }) {
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState(null);
  const [locked, setLocked] = useState(false);

  const openSource = useCallback(async (ref) => {
    if (typeof ref === 'object' && ref?.id && (ref?.pages || ref?.raw_text || ref?.tableRows)) {
      if (isAccessDeniedDocument(ref)) {
        setSource({ id: ref.id, locked: true, accessDenied: true });
        setLocked(true);
        setOpen(true);
        return;
      }
      setLocked(false);
      setSource(mergeSourceSpan(ref));
      setOpen(true);
      return;
    }
    try {
      const document = await fetchSourceDocument(ref);
      if (!document) return;
      if (isAccessDeniedDocument(document)) {
        setSource({ id: document.id ?? ref, locked: true, accessDenied: true });
        setLocked(true);
        setOpen(true);
        return;
      }
      setLocked(false);
      setSource(mergeSourceSpan(document));
      setOpen(true);
    } catch (error) {
      const code = error?.code ?? error?.message ?? '';
      if (code === 'access_denied' || String(code).includes('access_denied')) {
        const id = typeof ref === 'object' ? ref?.id ?? ref?.source_span_id : ref;
        setSource({ id, locked: true, accessDenied: true });
        setLocked(true);
        setOpen(true);
      }
    }
  }, []);

  const closeSource = useCallback(() => {
    setOpen(false);
    setLocked(false);
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
      <SourceDocumentModal open={open} source={source} locked={locked} onClose={closeSource} />
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
