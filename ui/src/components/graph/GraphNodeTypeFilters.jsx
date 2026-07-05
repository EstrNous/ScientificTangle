import { useTranslation } from 'react-i18next';
import { ALL_GRAPH_NODE_TYPES, GRAPH_NODE_COLORS } from './graphNodeTypes.js';

function TableIcon({ className = 'h-4 w-4' }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={2}
        d="M4 6h16M4 10h16M4 14h16M4 18h16M8 6v12M14 6v12"
      />
    </svg>
  );
}

function GraphIcon({ className = 'h-4 w-4' }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
      <circle cx="6" cy="6" r="2" strokeWidth={2} />
      <circle cx="18" cy="6" r="2" strokeWidth={2} />
      <circle cx="12" cy="18" r="2" strokeWidth={2} />
      <path strokeLinecap="round" strokeWidth={2} d="M8 6h8M7 8l4 8m6-8l-4 8" />
    </svg>
  );
}

export default function GraphNodeTypeFilters({
  activeTypes,
  onChange,
  viewMode = 'graph',
  onViewModeChange,
}) {
  const { t } = useTranslation();

  const toggleType = (type) => {
    if (activeTypes.includes(type)) {
      if (activeTypes.length === 1) return;
      onChange(activeTypes.filter((item) => item !== type));
      return;
    }
    onChange([...activeTypes, type]);
  };

  const selectAll = () => onChange([...ALL_GRAPH_NODE_TYPES]);
  const clearAll = () => onChange([ALL_GRAPH_NODE_TYPES[0]]);

  return (
    <div className="shrink-0 space-y-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wide text-nn-gray dark:text-slate-400">
          {t('graph.nodeTypeFilters')}
        </p>
        <div className="flex flex-wrap items-center gap-2 text-[11px]">
          <button
            type="button"
            onClick={selectAll}
            className="text-nn-blue hover:underline dark:text-sky-400"
          >
            {t('graph.selectAllTypes')}
          </button>
          <span className="text-nn-border dark:text-slate-600">|</span>
          <button
            type="button"
            onClick={clearAll}
            className="text-nn-gray hover:underline dark:text-slate-400"
          >
            {t('graph.resetTypes')}
          </button>
          <span className="text-nn-border dark:text-slate-600">|</span>
          <button
            type="button"
            onClick={() => onViewModeChange?.(viewMode === 'table' ? 'graph' : 'table')}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 font-medium transition-colors ${
              viewMode === 'table'
                ? 'border-nn-blue bg-nn-blue-light text-nn-blue dark:border-sky-600 dark:bg-slate-800 dark:text-sky-300'
                : 'border-nn-border bg-white text-nn-gray hover:border-nn-blue/40 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-400'
            }`}
            title={viewMode === 'table' ? t('graph.graphView') : t('graph.tableView')}
          >
            {viewMode === 'table' ? (
              <GraphIcon className="h-3.5 w-3.5" />
            ) : (
              <TableIcon className="h-3.5 w-3.5" />
            )}
            {viewMode === 'table' ? t('graph.graphView') : t('graph.tableView')}
          </button>
        </div>
      </div>
      <div className="flex flex-wrap gap-2">
        {ALL_GRAPH_NODE_TYPES.map((type) => {
          const isActive = activeTypes.includes(type);
          const color = GRAPH_NODE_COLORS[type] ?? GRAPH_NODE_COLORS.default;
          return (
            <button
              key={type}
              type="button"
              onClick={() => toggleType(type)}
              className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${
                isActive
                  ? 'border-transparent text-white'
                  : 'border-nn-border bg-white text-nn-gray dark:border-slate-600 dark:bg-slate-800 dark:text-slate-400'
              }`}
              style={isActive ? { backgroundColor: color } : undefined}
            >
              <span
                className="h-2 w-2 rounded-full"
                style={{ backgroundColor: isActive ? '#ffffff' : color }}
              />
              {t(`graph.nodeTypes.${type}`)}
            </button>
          );
        })}
      </div>
    </div>
  );
}
