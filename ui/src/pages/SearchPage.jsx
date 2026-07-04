import { useCallback, useState } from 'react';

import { useTranslation } from 'react-i18next';

import PageShell from '../components/shared/PageShell.jsx';

import Loader from '../components/shared/Loader.jsx';

import SourceLink from '../components/shared/SourceLink.jsx';

import SearchFilters from '../components/search/SearchFilters.jsx';

import { ensureAuth } from '../api/auth.js';

import { searchDocuments } from '../api/search.js';



const PAGE_SIZE = 20;



function parseGeoText(value) {

  return (value ?? '')

    .split(/[,;]/)

    .map((item) => item.trim())

    .filter(Boolean);

}



export default function SearchPage() {

  const { t } = useTranslation();

  const [question, setQuestion] = useState('');

  const [filters, setFilters] = useState({

    geoText: '',

    yearFrom: '',

    yearTo: '',

    numericValue: '',

    numericUnit: '',

    sourceTypes: [],

  });

  const [loading, setLoading] = useState(false);

  const [loadingMore, setLoadingMore] = useState(false);

  const [error, setError] = useState(null);

  const [results, setResults] = useState(null);

  const [limit, setLimit] = useState(PAGE_SIZE);



  const runSearch = useCallback(

    async ({ nextLimit = PAGE_SIZE, append = false } = {}) => {

      if (!question.trim()) return;

      if (append) {

        setLoadingMore(true);

      } else {

        setLoading(true);

      }

      setError(null);

      try {

        await ensureAuth();

        const data = await searchDocuments({

          question,

          geo: parseGeoText(filters.geoText),

          sourceTypes: filters.sourceTypes,

          yearFrom: filters.yearFrom,

          yearTo: filters.yearTo,

          numericValue: filters.numericValue,

          numericUnit: filters.numericUnit,

          limit: nextLimit,

        });

        setResults(data);

        setLimit(nextLimit);

      } catch (searchError) {

        setError(searchError?.message ?? 'search_failed');

        if (!append) {

          setResults(null);

        }

      } finally {

        setLoading(false);

        setLoadingMore(false);

      }

    },

    [filters, question],

  );



  const handleSearch = async (event) => {

    event.preventDefault();

    await runSearch({ nextLimit: PAGE_SIZE, append: false });

  };



  const handleLoadMore = async () => {

    await runSearch({ nextLimit: limit + PAGE_SIZE, append: true });

  };



  const canLoadMore = Boolean(

    results?.items?.length && results.total_found > results.items.length,

  );



  return (

    <PageShell>

      <div className="mx-auto flex h-full max-w-5xl flex-col gap-4 p-4">

        <form onSubmit={handleSearch} className="flex flex-col gap-3">

          <div className="flex gap-2">

            <input

              value={question}

              onChange={(event) => setQuestion(event.target.value)}

              placeholder={t('graph.searchPlaceholder')}

              className="flex-1 rounded-lg border border-nn-border px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"

            />

            <button type="submit" className="nn-btn-primary px-4 py-2 text-sm" disabled={loading}>

              {t('nav.search')}

            </button>

          </div>

          <SearchFilters filters={filters} onChange={setFilters} disabled={loading} />

        </form>



        {loading && <Loader />}

        {error && <p className="text-sm text-red-600">{t(`search.errors.${error}`, { defaultValue: error })}</p>}



        {results?.warnings?.length > 0 && (

          <ul className="space-y-1 rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100">

            {results.warnings.map((warning) => (

              <li key={warning}>{warning}</li>

            ))}

          </ul>

        )}



        {results?.items?.length > 0 && (

          <>

            <p className="text-xs text-nn-gray dark:text-slate-400">

              {t('search.resultsCount', {

                shown: results.items.length,

                total: results.total_found ?? results.items.length,

              })}

            </p>

            <ul className="space-y-3">

              {results.items.map((item) => (

                <li key={item.source?.source_span?.id} className="nn-card p-4 text-sm">

                  <p className="font-medium">{item.source?.document_title}</p>

                  <p className="mt-1 text-nn-gray dark:text-slate-400">

                    {(item.source?.source_span?.text ?? '').slice(0, 240)}

                  </p>

                  <p className="mt-2 text-xs text-nn-gray">

                    score: {item.relevance_score?.toFixed?.(3) ?? item.relevance_score}

                  </p>

                  <SourceLink sourceRef={item.source?.source_span?.id} className="mt-2 text-xs" />

                </li>

              ))}

            </ul>

            {canLoadMore && (

              <button

                type="button"

                onClick={handleLoadMore}

                disabled={loadingMore}

                className="self-center rounded-lg border border-nn-border px-4 py-2 text-sm font-medium text-nn-blue hover:bg-nn-blue-light disabled:opacity-50 dark:border-slate-600 dark:text-sky-300 dark:hover:bg-slate-800"

              >

                {loadingMore ? t('search.loadingMore') : t('search.loadMore')}

              </button>

            )}

          </>

        )}

      </div>

    </PageShell>

  );

}
