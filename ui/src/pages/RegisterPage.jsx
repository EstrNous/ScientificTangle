import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import AuthActionLink from '../components/auth/AuthActionLink.jsx';
import { authInputClassName, authOutlineButtonClassName, authSubmitClassName } from '../components/auth/authFormStyles.js';
import { mapAuthError, register } from '../api/auth.js';
import { validateRegisterForm } from '../utils/authValidation.js';

export default function RegisterPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fieldError, setFieldError] = useState(null);
  const [submitError, setSubmitError] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setFieldError(null);
    setSubmitError(null);

    const validationError = validateRegisterForm({
      username,
      email,
      password,
      confirmPassword,
    });
    if (validationError) {
      setFieldError(validationError);
      return;
    }

    setLoading(true);
    try {
      await register(username.trim(), email.trim(), password);
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
          {t('auth.registerTitle')}
        </h1>
        <p className="mt-2 text-sm text-nn-gray dark:text-slate-400">
          {t('auth.registerSubtitle')}
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
            {t('auth.username')}
          </span>
          <input
            type="text"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            placeholder={t('auth.usernamePlaceholder')}
            className={authInputClassName}
            disabled={loading}
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
            {t('auth.email')}
          </span>
          <input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder={t('auth.emailPlaceholder')}
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
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder={t('auth.passwordPlaceholder')}
            className={authInputClassName}
            disabled={loading}
          />
        </label>

        <label className="block space-y-1.5">
          <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
            {t('auth.confirmPassword')}
          </span>
          <input
            type="password"
            autoComplete="new-password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            placeholder={t('auth.confirmPasswordPlaceholder')}
            className={authInputClassName}
            disabled={loading}
          />
        </label>

        <p className="text-xs text-nn-gray dark:text-slate-400">{t('auth.passwordHint')}</p>

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
          {loading ? t('auth.registering') : t('auth.registerSubmit')}
        </button>
      </form>

      <AuthActionLink to="/login" className={`${authOutlineButtonClassName} mt-4`}>
        {t('auth.loginAction')}
      </AuthActionLink>
    </div>
  );
}
