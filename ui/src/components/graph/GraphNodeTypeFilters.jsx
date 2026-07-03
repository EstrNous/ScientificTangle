import { useTranslation } from 'react-i18next';
import { ALL_GRAPH_NODE_TYPES, GRAPH_NODE_COLORS } from './graphNodeTypes.js';

export default function GraphNodeTypeFilters({ activeTypes, onChange }) {
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
        <div className="flex gap-2 text-[11px]">
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
