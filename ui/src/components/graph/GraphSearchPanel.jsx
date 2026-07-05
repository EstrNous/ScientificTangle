import { useState } from 'react';
import { useTranslation } from 'react-i18next';

const GEO_OPTIONS = ['all', 'domestic', 'foreign', 'unknown'];
const MATERIAL_OPTIONS = ['all', 'Никель', 'Медь', 'Шахтная вода'];
const PROCESS_OPTIONS = ['all', 'Электроэкстракция', 'Обессоливание', 'Флотация'];

export default function GraphSearchPanel({ onSearch, isSearching }) {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const [material, setMaterial] = useState('all');
  const [process, setProcess] = useState('all');
  const [geo, setGeo] = useState('all');

  const handleSubmit = (event) => {
    event.preventDefault();
    onSearch?.({ query, material, process, geo });
  };

  const selectClass =
    'rounded-lg border border-nn-border bg-white px-3 py-2 text-sm text-gray-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100';

  return (
    <form onSubmit={handleSubmit} className="shrink-0 space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative min-w-[200px] flex-1">
          <svg
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-nn-gray dark:text-slate-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('graph.searchPlaceholder')}
            className="w-full rounded-lg border border-nn-border bg-white py-2 pl-9 pr-3 text-sm text-gray-900 placeholder:text-nn-gray focus:border-nn-blue focus:outline-none focus:ring-1 focus:ring-nn-blue dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100 dark:placeholder:text-slate-500"
          />
        </div>
        <select
          value={material}
          onChange={(e) => setMaterial(e.target.value)}
          className={selectClass}
          aria-label={t('graph.filterMaterial')}
        >
          {MATERIAL_OPTIONS.map((value) => (
            <option key={value} value={value}>
              {value === 'all' ? t('graph.filterAllMaterials') : value}
            </option>
          ))}
        </select>
        <select
          value={process}
          onChange={(e) => setProcess(e.target.value)}
          className={selectClass}
          aria-label={t('graph.filterProcess')}
        >
          {PROCESS_OPTIONS.map((value) => (
            <option key={value} value={value}>
              {value === 'all' ? t('graph.filterAllProcesses') : value}
            </option>
          ))}
        </select>
        <select
          value={geo}
          onChange={(e) => setGeo(e.target.value)}
          className={selectClass}
          aria-label={t('graph.filterGeo')}
        >
          {GEO_OPTIONS.map((value) => (
            <option key={value} value={value}>
              {t(`graph.geo.${value}`)}
            </option>
          ))}
        </select>
        <button
          type="submit"
          disabled={isSearching}
          className="rounded-lg bg-nn-blue px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-nn-blue-dark disabled:opacity-60"
        >
          {isSearching ? t('graph.searching') : t('graph.searchButton')}
        </button>
      </div>
    </form>
  );
}
