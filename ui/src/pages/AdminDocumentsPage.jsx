import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { fetchDocumentCatalog } from '../api/documents.js';
import { AdminSubNav } from '../components/admin/index.js';
import DocumentCatalogTable from '../components/admin/DocumentCatalogTable.jsx';

const FILTERS = [
  { id: '', labelKey: 'admin.documents.filters.all' },
  { id: 'completed', labelKey: 'admin.documents.filters.completed' },
  { id: 'failed', labelKey: 'admin.documents.filters.failed' },
  { id: 'no_index', labelKey: 'admin.documents.filters.noIndex' },
  { id: 'no_source_spans', labelKey: 'admin.documents.filters.noSourceSpans' },
];

export default function AdminDocumentsPage() {
  const { t } = useTranslation();
  const [status, setStatus] = useState('');
  const [catalog, setCatalog] = useState({ items: [], total: 0 });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const params = { limit: 100 };
        if (status === 'no_index' || status === 'no_source_spans') {
          params.filter = status;
        } else if (status) {
          params.status = status;
        }
        const payload = await fetchDocumentCatalog(params);
        if (!cancelled) {
          setCatalog(payload);
        }
      } catch (loadError) {
        if (!cancelled) {
          setError(loadError.message ?? String(loadError));
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [status]);

  return (
    <div className="flex h-full flex-col gap-4 p-4">
      <AdminSubNav />
      <div>
        <h1 className="text-xl font-semibold">{t('admin.documents.title')}</h1>
        <p className="text-sm text-slate-500">{t('admin.documents.subtitle', { total: catalog.total })}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {FILTERS.map((filter) => (
          <button
            key={filter.id || 'all'}
            type="button"
            onClick={() => setStatus(filter.id)}
            className={`rounded-lg px-3 py-1.5 text-sm ${
              status === filter.id ? 'bg-nn-blue text-white' : 'bg-slate-100 dark:bg-slate-800'
            }`}
          >
            {t(filter.labelKey)}
          </button>
        ))}
      </div>
      {loading ? <p>{t('common.loading')}</p> : null}
      {error ? <p className="text-red-600">{error}</p> : null}
      {!loading && !error ? <DocumentCatalogTable items={catalog.items ?? []} /> : null}
    </div>
  );
}
