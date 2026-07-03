import { useTranslation } from 'react-i18next';
import GraphPanelShell from './GraphPanelShell.jsx';

export default function GraphSearchResults({
  results,
  hasSearched,
  expanded,
  onToggleExpand,
  className = '',
}) {
  const { t } = useTranslation();

  return (
    <GraphPanelShell
      title={t('graph.searchResults')}
      expanded={expanded}
      onToggleExpand={onToggleExpand}
      className={className}
    >
      {!hasSearched && (
        <p className="text-xs text-nn-gray dark:text-slate-400">{t('graph.searchHint')}</p>
      )}
      {hasSearched && results.length === 0 && (
        <p className="text-xs text-nn-gray dark:text-slate-400">{t('graph.noResults')}</p>
      )}
      {results.length > 0 && (
        <ul
          className={`space-y-2 ${
            expanded
              ? ''
              : 'scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 overflow-y-auto'
          }`}
        >
          {results.map((item) => (
            <li
              key={item.id}
              className="rounded-lg border border-nn-border bg-nn-gray-light p-2.5 text-xs dark:border-slate-600 dark:bg-slate-800"
            >
              <p className="font-medium leading-snug text-gray-900 dark:text-slate-100">{item.title}</p>
              <p className="mt-1 text-nn-gray dark:text-slate-400">
                {item.material} · {item.process} · {item.year} · {t(`graph.geoLabel.${item.geoKey}`)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </GraphPanelShell>
  );
}
