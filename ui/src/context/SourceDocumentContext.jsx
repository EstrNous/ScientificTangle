import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { fetchSourceDocument, mergeSourceSpan } from '../api/sourceResolver/index.js';
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
    try {
      const document = await fetchSourceDocument(ref);
      if (!document) return;
      setSource(mergeSourceSpan(document));
      setOpen(true);
    } catch {
      return;
    }
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
