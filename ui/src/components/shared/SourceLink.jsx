import { useSourceDocument } from '../../context/SourceDocumentContext.jsx';
import { resolveSourceRef } from '../../api/mock/sourceCatalog.js';
import { useMock } from '../../api/client.js';

export default function SourceLink({ sourceRef, source, children, className = '', onOpen }) {
  const { openSource } = useSourceDocument();
  const label = children ?? sourceRef ?? source?.title;
  const spanId = source?.source_span_id ?? sourceRef;
  const resolved = useMock ? resolveSourceRef(sourceRef) ?? resolveSourceRef(source) : null;

  if (!useMock && spanId) {
    return (
      <button
        type="button"
        onClick={() => {
          openSource(spanId);
          onOpen?.();
        }}
        className={`text-left text-nn-blue hover:underline dark:text-sky-400 ${className}`}
      >
        {label}
      </button>
    );
  }

  if (!resolved) {
    return <span className={className}>{label}</span>;
  }

  return (
    <button
      type="button"
      onClick={() => {
        openSource(resolved);
        onOpen?.();
      }}
      className={`text-left text-nn-blue hover:underline dark:text-sky-400 ${className}`}
    >
      {label}
    </button>
  );
}
