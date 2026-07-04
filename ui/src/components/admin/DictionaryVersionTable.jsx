import { useTranslation } from 'react-i18next';
import AdminPanelShell from './AdminPanelShell.jsx';

const STATUS_STYLES = {
  active: 'bg-emerald-100 text-emerald-900 dark:bg-emerald-500/20 dark:text-emerald-100',
  validated: 'bg-nn-blue-light text-nn-blue dark:bg-slate-800 dark:text-sky-300',
  inactive: 'bg-slate-200 text-slate-700 dark:bg-slate-700 dark:text-slate-200',
  validation_failed: 'bg-red-100 text-red-900 dark:bg-red-500/20 dark:text-red-100',
};

export default function DictionaryVersionTable({
  versions,
  activatingId,
  onActivate,
  expanded,
  onToggleExpand,
}) {
  const { t } = useTranslation();

  if (!versions?.length) {
    return (
      <AdminPanelShell
        title={t('admin.dictionariesTitle')}
        expanded={expanded}
        onToggleExpand={onToggleExpand}
      >
        <p className="text-sm text-nn-gray dark:text-slate-400">{t('admin.dictionariesEmpty')}</p>
      </AdminPanelShell>
    );
  }

  return (
    <AdminPanelShell
      title={t('admin.dictionariesTitle')}
      expanded={expanded}
      onToggleExpand={onToggleExpand}
    >
      <div className="min-h-0 flex-1 overflow-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="sticky top-0 z-10 bg-white text-xs uppercase tracking-wide text-nn-gray dark:bg-slate-900 dark:text-slate-400">
            <tr>
              <th className="px-3 py-2 font-medium">{t('admin.dictionaryColumns.version')}</th>
              <th className="px-3 py-2 font-medium">{t('admin.dictionaryColumns.status')}</th>
              <th className="px-3 py-2 font-medium">{t('admin.dictionaryColumns.files')}</th>
              <th className="px-3 py-2 font-medium">{t('admin.dictionaryColumns.created')}</th>
              <th className="px-3 py-2 font-medium">{t('admin.dictionaryColumns.actions')}</th>
            </tr>
          </thead>
          <tbody>
            {versions.map((version) => {
              const canActivate = version.status !== 'active' && version.status !== 'validation_failed';
              return (
                <tr key={version.id} className="border-t border-nn-border dark:border-slate-700">
                  <td className="px-3 py-2 font-medium text-gray-900 dark:text-slate-100">
                    {version.version}
                  </td>
                  <td className="px-3 py-2">
                    <span
                      className={`rounded-full px-2 py-0.5 text-[11px] font-medium ${
                        STATUS_STYLES[version.status] ?? STATUS_STYLES.inactive
                      }`}
                    >
                      {t(`admin.dictionaryStatus.${version.status}`, { defaultValue: version.status })}
                    </span>
                  </td>
                  <td className="px-3 py-2 tabular-nums text-nn-gray dark:text-slate-400">
                    {version.filesCount}
                  </td>
                  <td className="px-3 py-2 text-xs text-nn-gray dark:text-slate-400">
                    {version.createdAt ? new Date(version.createdAt).toLocaleString() : '—'}
                  </td>
                  <td className="px-3 py-2">
                    {canActivate ? (
                      <button
                        type="button"
                        disabled={activatingId === version.id}
                        onClick={() => onActivate(version.id)}
                        className="rounded-lg border border-nn-border px-3 py-1 text-xs font-medium text-nn-blue hover:bg-nn-blue-light disabled:opacity-50 dark:border-slate-600 dark:text-sky-300 dark:hover:bg-slate-800"
                      >
                        {activatingId === version.id
                          ? t('admin.dictionaryActivating')
                          : t('admin.dictionaryActivate')}
                      </button>
                    ) : (
                      <span className="text-xs text-nn-gray dark:text-slate-500">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </AdminPanelShell>
  );
}
