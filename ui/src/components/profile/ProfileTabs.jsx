import { useTranslation } from 'react-i18next';

const TAB_ITEMS = [
  { id: 'account', labelKey: 'profile.accountTitle' },
  { id: 'password', labelKey: 'profile.passwordTitle' },
  { id: 'security', labelKey: 'profile.securityTitle' },
];

export default function ProfileTabs({ activeTab, onChange }) {
  const { t } = useTranslation();

  return (
    <div className="shrink-0 border-b border-nn-border dark:border-slate-700">
      <nav className="flex flex-wrap gap-2" role="tablist" aria-label={t('profile.title')}>
        {TAB_ITEMS.map((tab) => {
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => onChange(tab.id)}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-nn-blue-light text-nn-blue dark:bg-slate-800 dark:text-sky-300'
                  : 'text-nn-gray hover:bg-nn-gray-light hover:text-gray-900 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100'
              }`}
            >
              {t(tab.labelKey)}
            </button>
          );
        })}
      </nav>
    </div>
  );
}
