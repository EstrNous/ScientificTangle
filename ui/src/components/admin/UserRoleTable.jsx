import { useTranslation } from 'react-i18next';
import { ROLES } from '../../stores/authStore.js';

const ROLE_OPTIONS = Object.values(ROLES);

export default function UserRoleTable({ users, onRoleChange, onActiveToggle }) {
  const { t } = useTranslation();

  if (!users?.length) return null;

  return (
    <div className="nn-card p-4">
      <p className="mb-3 text-sm font-semibold text-gray-900 dark:text-slate-100">
        {t('admin.usersTitle')}
      </p>
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
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
