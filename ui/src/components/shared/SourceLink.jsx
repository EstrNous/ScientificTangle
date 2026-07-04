import { useSourceDocument } from '../../context/SourceDocumentContext.jsx';
import { useSourceRefRenderer } from '../../hooks/useSourceRefRenderer.js';

export default function SourceLink({ sourceRef, source, children, className = '', onOpen }) {
  const { openSource } = useSourceDocument();
  const { label, openRef, isInteractive } = useSourceRefRenderer({ sourceRef, source, children });

  if (!isInteractive) {
    return <span className={className}>{label}</span>;
  }

  return (
    <button
      type="button"
      onClick={() => {
        openSource(openRef);
        onOpen?.();
      }}
      className={`text-left text-nn-blue hover:underline dark:text-sky-400 ${className}`}
    >
      {label}
    </button>
  );
}
