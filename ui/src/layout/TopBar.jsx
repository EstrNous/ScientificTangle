import { useTranslation } from 'react-i18next';
import AppLogo from '../components/shared/AppLogo.jsx';
import DarkModeToggle from '../components/shared/DarkModeToggle.jsx';
import NotificationBell from '../components/shared/NotificationBell.jsx';
import RoleSwitcher from '../components/shared/RoleSwitcher.jsx';
import ProfileButton from '../components/shared/ProfileButton.jsx';
import ServiceHealthIndicator from '../components/shared/ServiceHealthIndicator.jsx';
import { useLocaleStore } from '../stores/localeStore.js';
import { isDevRoleSwitcherEnabled } from '../utils/uiFeatureFlags.js';
import i18n from '../i18n/index.js';

export default function TopBar() {
  const { t } = useTranslation();
  const locale = useLocaleStore((s) => s.locale);
  const setLocale = useLocaleStore((s) => s.setLocale);

  return (
    <header className="shrink-0 border-b border-nn-border bg-white px-3 py-3 sm:px-6 sm:py-4 dark:border-slate-700 dark:bg-slate-900">
      <div className="flex items-center justify-between gap-3 sm:gap-6">
        <div className="flex min-w-0 items-center gap-2 sm:gap-3">
          <AppLogo />
          <span className="truncate text-base font-semibold text-gray-900 sm:text-lg dark:text-slate-100">
            {t('app.title')}
          </span>
        </div>

        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <ServiceHealthIndicator />
          {isDevRoleSwitcherEnabled() && <RoleSwitcher />}
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
          <ProfileButton />
          <NotificationBell />
        </div>
      </div>
    </header>
  );
}
