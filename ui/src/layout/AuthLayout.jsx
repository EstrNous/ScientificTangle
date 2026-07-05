import { Outlet } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import AppLogo from '../components/shared/AppLogo.jsx';
import DarkModeToggle from '../components/shared/DarkModeToggle.jsx';
import { useLocaleStore } from '../stores/localeStore.js';
import i18n from '../i18n/index.js';

export default function AuthLayout() {
  const { t } = useTranslation();
  const locale = useLocaleStore((s) => s.locale);
  const setLocale = useLocaleStore((s) => s.setLocale);

  return (
    <div className="flex min-h-screen flex-col bg-nn-gray-light text-gray-900 dark:bg-slate-950 dark:text-slate-100">
      <header className="flex items-center justify-between border-b border-nn-border bg-white px-6 py-4 dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-center gap-3">
          <AppLogo />
          <span className="text-lg font-semibold">{t('app.title')}</span>
        </div>
        <div className="flex items-center gap-3">
          <DarkModeToggle />
          <button
            type="button"
            onClick={() => {
              const next = locale === 'ru' ? 'en' : 'ru';
              setLocale(next);
              i18n.changeLanguage(next);
            }}
            className="rounded-lg border border-nn-border px-3 py-1.5 text-sm text-nn-gray hover:bg-nn-gray-light dark:border-slate-600 dark:text-slate-300 dark:hover:bg-slate-800"
          >
            {locale === 'ru' ? 'EN' : 'RU'}
          </button>
        </div>
      </header>
      <main className="flex flex-1 items-center justify-center p-6">
        <Outlet />
      </main>
    </div>
  );
}
