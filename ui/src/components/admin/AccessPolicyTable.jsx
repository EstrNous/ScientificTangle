import { useTranslation } from 'react-i18next';

const LEVEL_STYLES = {
  public: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300',
  internal: 'bg-nn-blue-light text-nn-blue dark:bg-slate-800 dark:text-sky-300',
  confidential: 'bg-amber-50 text-amber-800 dark:bg-amber-950 dark:text-amber-200',
  restricted: 'bg-gray-100 text-gray-700 dark:bg-slate-800 dark:text-slate-300',
};

export default function AccessPolicyTable({ policies }) {
  const { t } = useTranslation();

  if (!policies?.length) return null;

  return (
    <div className="nn-card p-4">
      <p className="mb-3 text-sm font-semibold text-gray-900 dark:text-slate-100">
        {t('admin.accessTitle')}
      </p>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[560px] border-collapse text-xs">
          <thead>
            <tr className="text-left text-nn-gray dark:text-slate-400">
              <th className="border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                {t('admin.document')}
              </th>
              <th className="border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                {t('admin.accessLevel')}
              </th>
              <th className="border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                {t('admin.allowedRoles')}
              </th>
              <th className="border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                {t('admin.export')}
              </th>
            </tr>
          </thead>
          <tbody>
            {policies.map((policy) => (
              <tr key={policy.id} className="hover:bg-nn-gray-light/60 dark:hover:bg-slate-800/50">
                <td className="border-b border-nn-border px-2 py-2.5 font-medium text-gray-900 dark:border-slate-700 dark:text-slate-100">
                  {policy.document}
                </td>
                <td className="border-b border-nn-border px-2 py-2.5 dark:border-slate-700">
                  <span
                    className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                      LEVEL_STYLES[policy.level] ?? LEVEL_STYLES.internal
                    }`}
                  >
                    {t(`admin.levels.${policy.level}`, { defaultValue: policy.level })}
                  </span>
                </td>
                <td className="border-b border-nn-border px-2 py-2.5 text-nn-gray dark:border-slate-700 dark:text-slate-400">
                  {policy.roles.map((role) => t(`roles.${role}`)).join(', ')}
                </td>
                <td className="border-b border-nn-border px-2 py-2.5 dark:border-slate-700">
                  {policy.export_allowed ? t('admin.exportYes') : t('admin.exportNo')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
