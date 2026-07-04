import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import SourceLink from '../components/shared/SourceLink.jsx';
import { apiGet } from '../api/client.js';
import { ensureAuth } from '../api/auth.js';

const real = { real: true };

export default function SearchPage() {
  const { t } = useTranslation();
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [results, setResults] = useState(null);

  const handleSearch = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await ensureAuth();
      const params = new URLSearchParams({ question: question.trim(), limit: '20' });
      const data = await apiGet(`/search?${params.toString()}`, real);
      setResults(data);
    } catch (searchError) {
      setError(searchError?.message ?? 'search_failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageShell>
      <div className="mx-auto flex h-full max-w-4xl flex-col gap-4 p-4">
        <form onSubmit={handleSearch} className="flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder={t('graph.searchPlaceholder')}
            className="flex-1 rounded-lg border border-nn-border px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
          />
          <button type="submit" className="nn-btn-primary px-4 py-2 text-sm">
            {t('nav.search')}
          </button>
        </form>
        {loading && <Loader />}
        {error && <p className="text-sm text-red-600">{error}</p>}
        {results?.items?.length > 0 && (
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
        )}
      </div>
    </PageShell>
  );
}
