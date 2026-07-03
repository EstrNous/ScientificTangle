import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { mergeSourceSpan, resolveSourceRef } from '../api/mock/sourceCatalog.js';
import SourceDocumentModal from '../components/shared/SourceDocumentModal.jsx';

const SourceDocumentContext = createContext(null);

export function SourceDocumentProvider({ children }) {
  const [open, setOpen] = useState(false);
  const [source, setSource] = useState(null);

  const openSource = useCallback((ref) => {
    const resolved = typeof ref === 'object' && ref?.id && ref?.pages ? ref : resolveSourceRef(ref);
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
