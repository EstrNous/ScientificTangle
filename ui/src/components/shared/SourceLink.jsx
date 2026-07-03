import { resolveSourceRef } from '../../api/mock/sourceCatalog.js';
import { useSourceDocument } from '../../context/SourceDocumentContext.jsx';

export default function SourceLink({ sourceRef, source, children, className = '' }) {
  const { openSource } = useSourceDocument();
  const label = children ?? sourceRef ?? source?.title;
  const resolved =
    resolveSourceRef(sourceRef) ??
    resolveSourceRef(source) ??
    (source?.author && source?.date ? resolveSourceRef(`${source.author}, ${source.date}`) : null);

  if (!resolved) {
    return <span className={className}>{label}</span>;
  }

  return (
    <button
      type="button"
      onClick={() => openSource(resolved)}
      className={`text-left text-nn-blue hover:underline dark:text-sky-400 ${className}`}
    >
      {label}
    </button>
  );
}
