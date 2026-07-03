import { useTranslation } from 'react-i18next';

export default function GraphSearchResults({ results, hasSearched }) {
  const { t } = useTranslation();

  return (
    <div className="nn-card flex min-h-0 flex-col p-3">
      <p className="mb-2 shrink-0 text-xs font-semibold uppercase tracking-wide text-nn-gray dark:text-slate-400">
        {t('graph.searchResults')}
      </p>
      {!hasSearched && (
        <p className="text-xs text-nn-gray dark:text-slate-400">{t('graph.searchHint')}</p>
      )}
      {hasSearched && results.length === 0 && (
        <p className="text-xs text-nn-gray dark:text-slate-400">{t('graph.noResults')}</p>
      )}
      <ul className="scrollbar-thin scrollbar-thumb-nn-border dark:scrollbar-thumb-slate-600 max-h-48 space-y-2 overflow-y-auto">
        {results.map((item) => (
          <li
            key={item.id}
            className="rounded-lg border border-nn-border bg-nn-gray-light p-2 text-xs dark:border-slate-600 dark:bg-slate-800"
          >
            <p className="font-medium text-gray-900 dark:text-slate-100">{item.title}</p>
            <p className="mt-1 text-nn-gray dark:text-slate-400">
              {item.material} · {item.process} · {item.year} · {t(`graph.geoLabel.${item.geoKey}`)}
            </p>
          </li>
        ))}
      </ul>
    </div>
  );
}
