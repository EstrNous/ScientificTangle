import { useTranslation } from 'react-i18next';
import { ROLES } from '../../stores/authStore.js';
import AdminPanelShell from './AdminPanelShell.jsx';
import SourceLink from '../shared/SourceLink.jsx';

const LEVEL_OPTIONS = ['public', 'internal', 'confidential', 'restricted'];
const ROLE_OPTIONS = Object.values(ROLES);

export default function AccessPolicyTable({
  policies,
  onLevelChange,
  onRoleToggle,
  onExportToggle,
  onSave,
  dirtyPolicyIds = [],
  savingPolicyId,
  expanded,
  onToggleExpand,
}) {
  const { t } = useTranslation();

  if (!policies?.length) return null;

  return (
    <AdminPanelShell
      title={t('admin.accessTitle')}
      expanded={expanded}
      onToggleExpand={onToggleExpand}
    >
      <p className="mb-3 text-[11px] leading-relaxed text-nn-gray dark:text-slate-400">
        {t('admin.accessHint')}
      </p>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[720px] border-collapse text-xs">
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
              <th className="w-20 border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                <span className="sr-only">{t('admin.saveRow')}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {policies.map((policy) => (
              <tr key={policy.id} className="hover:bg-nn-gray-light/60 dark:hover:bg-slate-800/50">
                <td className="border-b border-nn-border px-2 py-2.5 font-medium text-gray-900 dark:border-slate-700 dark:text-slate-100">
                  <SourceLink sourceRef={policy.title ?? policy.documentId}>{policy.title ?? policy.documentId}</SourceLink>
                </td>
                <td className="border-b border-nn-border px-2 py-2.5 dark:border-slate-700">
                  <select
                    value={policy.level}
                    onChange={(e) => onLevelChange?.(policy.id, e.target.value)}
                    title={t(`admin.levelDescriptions.${policy.level}`)}
                    className="w-full max-w-[11rem] rounded-lg border border-nn-border bg-white px-2 py-1 text-xs text-gray-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                  >
                    {LEVEL_OPTIONS.map((level) => (
                      <option key={level} value={level} title={t(`admin.levelDescriptions.${level}`)}>
                        {t(`admin.levels.${level}`, { defaultValue: level })}
                      </option>
                    ))}
                  </select>
                </td>
                <td className="border-b border-nn-border px-2 py-2.5 dark:border-slate-700">
                  <div className="flex max-w-[18rem] flex-wrap gap-1">
                    {ROLE_OPTIONS.map((role) => {
                      const active = policy.roles.includes(role);
                      return (
                        <button
                          key={role}
                          type="button"
                          onClick={() => onRoleToggle?.(policy.id, role)}
                          title={t(active ? 'admin.roleRemoveHint' : 'admin.roleAddHint', {
                            role: t(`roles.${role}`),
                          })}
                          className={`rounded-full px-2 py-0.5 text-[10px] font-medium transition-colors ${
                            active
                              ? 'bg-nn-blue-light text-nn-blue dark:bg-sky-950 dark:text-sky-300'
                              : 'border border-dashed border-nn-border text-nn-gray dark:border-slate-600 dark:text-slate-500'
                          }`}
                        >
                          {t(`roles.${role}`)}
                        </button>
                      );
                    })}
                  </div>
                </td>
                <td className="border-b border-nn-border px-2 py-2.5 dark:border-slate-700">
                  <button
                    type="button"
                    onClick={() => onExportToggle?.(policy.id)}
                    title={t(policy.exportAllowed ? 'admin.exportDisableHint' : 'admin.exportEnableHint')}
                    className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold ${
                      policy.exportAllowed
                        ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950 dark:text-emerald-300'
                        : 'bg-gray-100 text-gray-600 dark:bg-slate-800 dark:text-slate-400'
                    }`}
                  >
                    {policy.exportAllowed ? t('admin.exportYes') : t('admin.exportNo')}
                  </button>
                </td>
                <td className="border-b border-nn-border px-2 py-2.5 text-center dark:border-slate-700">
                  {dirtyPolicyIds.includes(policy.id) && (
                    <button
                      type="button"
                      onClick={() => onSave?.(policy.id)}
                      disabled={savingPolicyId === policy.id}
                      className="rounded-md border border-nn-blue px-2 py-0.5 text-[10px] font-medium text-nn-blue hover:bg-nn-blue-light disabled:opacity-50 dark:border-sky-600 dark:text-sky-300"
                    >
                      {savingPolicyId === policy.id ? t('admin.saving') : t('admin.saveRow')}
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </AdminPanelShell>
  );
}
