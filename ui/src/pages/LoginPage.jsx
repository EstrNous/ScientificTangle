import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import AuthActionLink from '../components/auth/AuthActionLink.jsx';
import {
  authInputClassName,
  authMutedButtonClassName,
  authOutlineButtonClassName,
  authSubmitClassName,
} from '../components/auth/authFormStyles.js';
import { login, mapAuthError } from '../api/auth.js';
import { validateLoginForm } from '../utils/authValidation.js';

export default function LoginPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [fieldError, setFieldError] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFieldError(null);
    setSubmitError(null);

    const validationError = validateLoginForm({ identifier, password });
    if (validationError) {
      setFieldError(validationError);
      return;
    }

    setLoading(true);
    try {
      await login(identifier.trim(), password);
      navigate('/chat', { replace: true });
    } catch (error) {
      const code = mapAuthError(error);
      setSubmitError(code);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="nn-card w-full max-w-md p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-gray-900 dark:text-slate-100">
          {t('auth.loginTitle')}
        </h1>
        <p className="mt-2 text-sm text-nn-gray dark:text-slate-400">{t('auth.loginSubtitle')}</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
            {t('auth.identifier')}
          </span>
          <input
            type="text"
            autoComplete="username"
            value={identifier}
            onChange={(event) => setIdentifier(event.target.value)}
            placeholder={t('auth.identifierPlaceholder')}
            className={authInputClassName}
            disabled={loading}
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
            {t('auth.password')}
          </span>
          <input
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder={t('auth.loginPasswordPlaceholder')}
            className={authInputClassName}
            disabled={loading}
          />
        </label>

        {fieldError && (
          <p className="text-sm text-red-600 dark:text-red-400" role="alert">
            {t(`auth.errors.${fieldError}`)}
          </p>
        )}
        {submitError && (
          <p className="text-sm text-red-600 dark:text-red-400" role="alert">
            {t(`auth.errors.${submitError}`, { defaultValue: t('auth.errors.unknown') })}
          </p>
        )}

        <button type="submit" disabled={loading} className={authSubmitClassName}>
          {loading ? t('auth.loggingIn') : t('auth.loginSubmit')}
        </button>
      </form>

      <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <AuthActionLink to="/forgot-password" className={authMutedButtonClassName}>
          {t('auth.forgotPasswordAction')}
        </AuthActionLink>
        <AuthActionLink to="/register" className={authOutlineButtonClassName}>
          {t('auth.registerAction')}
        </AuthActionLink>
      </div>
    </div>
  );
}
