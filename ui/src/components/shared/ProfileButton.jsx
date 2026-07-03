import { useTranslation } from 'react-i18next';
import { useAuthStore } from '../../stores/authStore.js';

function ProfileIcon() {
  return (
    <svg className="h-5 w-5" fill="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
    </svg>
  );
}

export default function ProfileButton() {
  const { t } = useTranslation();
  const role = useAuthStore((s) => s.role);

  return (
    <button
      type="button"
      aria-label={t('common.profile')}
      title={t(`roles.${role}`)}
      className="flex h-9 w-9 items-center justify-center rounded-full border border-nn-blue bg-nn-blue-light text-nn-blue transition-colors hover:bg-nn-blue hover:text-white dark:bg-slate-800 dark:hover:bg-nn-blue"
    >
      <ProfileIcon />
    </button>
  );
}
