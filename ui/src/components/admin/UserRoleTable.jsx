import { useTranslation } from 'react-i18next';
import { ROLES } from '../../stores/authStore.js';
import AdminPanelShell from './AdminPanelShell.jsx';
import { DeleteIcon } from './AdminIcons.jsx';

const ROLE_OPTIONS = Object.values(ROLES);

export default function UserRoleTable({
  users,
  onRoleChange,
  onActiveToggle,
  onDelete,
  expanded,
  onToggleExpand,
}) {
  const { t } = useTranslation();

  return (
    <AdminPanelShell
      title={t('admin.usersTitle')}
      expanded={expanded}
      onToggleExpand={onToggleExpand}
    >
      {!users?.length ? (
        <p className="text-xs text-nn-gray dark:text-slate-400">{t('admin.usersEmpty')}</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[520px] border-collapse text-xs">
            <thead>
              <tr className="text-left text-nn-gray dark:text-slate-400">
                <th className="border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                  {t('admin.userName')}
                </th>
                <th className="border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                  {t('admin.userEmail')}
                </th>
                <th className="border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                  {t('admin.userRole')}
                </th>
                <th className="border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                  {t('admin.userStatus')}
                </th>
                <th className="w-10 border-b border-nn-border px-2 py-2 font-medium dark:border-slate-600">
                  <span className="sr-only">{t('admin.userActions')}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-nn-gray-light/60 dark:hover:bg-slate-800/50">
                  <td className="border-b border-nn-border px-2 py-2.5 font-medium text-gray-900 dark:border-slate-700 dark:text-slate-100">
                    {user.name}
                  </td>
                  <td className="border-b border-nn-border px-2 py-2.5 text-nn-gray dark:border-slate-700 dark:text-slate-400">
                    {user.email}
                  </td>
                  <td className="border-b border-nn-border px-2 py-2.5 dark:border-slate-700">
                    <select
                      value={user.role}
                      onChange={(e) => onRoleChange?.(user.id, e.target.value)}
                      className="w-full max-w-[10rem] rounded-lg border border-nn-border bg-white px-2 py-1 text-xs text-gray-900 dark:border-slate-600 dark:bg-slate-800 dark:text-slate-100"
                    >
                      {ROLE_OPTIONS.map((role) => (
                        <option key={role} value={role}>
                          {t(`roles.${role}`)}
                        </option>
                      ))}
                    </select>
                  </td>
                  <td className="border-b border-nn-border px-2 py-2.5 dark:border-slate-700">
                    <button
                      type="button"
                      onClick={() => onActiveToggle?.(user.id)}
                      className={`rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${
                        user.active
                          ? 'bg-nn-blue-light text-nn-blue dark:bg-slate-800 dark:text-sky-300'
                          : 'bg-gray-100 text-gray-600 dark:bg-slate-800 dark:text-slate-400'
                      }`}
                    >
                      {user.active ? t('admin.statusActive') : t('admin.statusInactive')}
                    </button>
                  </td>
                  <td className="border-b border-nn-border px-2 py-2.5 text-center dark:border-slate-700">
                    <button
                      type="button"
                      onClick={() => onDelete?.(user.id)}
                      className="inline-flex rounded-md p-1 text-nn-gray transition-colors hover:bg-nn-gray-light hover:text-gray-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100"
                      title={t('admin.deleteUser')}
                      aria-label={t('admin.deleteUser')}
                    >
                      <DeleteIcon className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AdminPanelShell>
  );
}
