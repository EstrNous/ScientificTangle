import KnowledgeGraph from './KnowledgeGraph.jsx';

export default function LocalGraph({ subgraph, inline = false }) {
  const graph = (
    <div className="h-48 overflow-hidden rounded-lg border border-nn-border dark:border-slate-600">
      <KnowledgeGraph subgraph={subgraph} />
    </div>
  );

  if (inline) {
    return (
      <div>
        <p className="mb-2 text-sm font-semibold text-gray-900 dark:text-slate-100">Контекст графа</p>
        {graph}
      </div>
    );
  }

  return (
    <div className="nn-card overflow-hidden p-3">
      <p className="mb-2 text-sm font-semibold text-gray-900 dark:text-slate-100">Контекст графа</p>
      {graph}
    </div>
  );
}
