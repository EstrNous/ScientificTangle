import { useTranslation } from 'react-i18next';
import { Link } from 'react-router-dom';
import AuthActionLink from '../components/auth/AuthActionLink.jsx';
import {
  authMutedButtonClassName,
  authOutlineButtonClassName,
} from '../components/auth/authFormStyles.js';

export default function ForgotPasswordPage() {
  const { t } = useTranslation();

  return (
    <div className="nn-card w-full max-w-md p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-slate-100">
          {t('auth.forgotPasswordTitle')}
        </h1>
        <p className="mt-2 text-sm text-nn-gray dark:text-slate-400">
          {t('auth.forgotPasswordSubtitle')}
        </p>
      </div>

      <p className="rounded-lg border border-nn-border bg-nn-gray-light/60 px-4 py-3 text-sm text-gray-700 dark:border-slate-600 dark:bg-slate-800/60 dark:text-slate-300">
        {t('auth.forgotPasswordHint')}
      </p>

      <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <AuthActionLink to="/login" className={authOutlineButtonClassName}>
          {t('auth.backToLogin')}
        </AuthActionLink>
        <Link to="/register" className={authMutedButtonClassName}>
          {t('auth.registerAction')}
        </Link>
      </div>
    </div>
  );
}
