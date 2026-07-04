import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import ProfileSection from '../components/profile/ProfileSection.jsx';
import ProfileTabs from '../components/profile/ProfileTabs.jsx';
import { authInputClassName, authSubmitClassName } from '../components/auth/authFormStyles.js';
import {
  changePassword,
  deactivateAccount,
  logout,
  logoutAll,
  mapAuthError,
  updateProfile,
} from '../api/auth.js';
import { useAuthStore } from '../stores/authStore.js';
import { loadInterestsProfile, saveInterestsProfile } from '../utils/interestsWorkflow.js';
import { useMock } from '../api/client.js';
import { loadUserInterests } from '../utils/interestsStorage.js';
import {
  validatePasswordChangeForm,
  validateProfileUpdateForm,
} from '../utils/profileValidation.js';

const outlineButtonClassName =
  'rounded-lg border border-nn-border bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:border-nn-blue hover:bg-nn-blue-light hover:text-nn-blue disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-600 dark:bg-slate-900 dark:text-slate-200 dark:hover:border-nn-blue dark:hover:bg-slate-800';

const dangerButtonClassName =
  'rounded-lg border border-red-300 bg-white px-4 py-2 text-sm font-medium text-red-700 transition-colors hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-red-800 dark:bg-slate-900 dark:text-red-300 dark:hover:bg-red-950/40';

function AccountSummary({ user, role, t }) {
  return (
    <dl className="grid gap-2 sm:grid-cols-2">
      <div>
        <dt className="text-xs uppercase tracking-wide text-nn-gray dark:text-slate-400">
          {t('auth.username')}
        </dt>
        <dd className="mt-1 text-sm font-medium text-gray-900 dark:text-slate-100">
          {user?.username ?? '—'}
        </dd>
      </div>
      <div>
        <dt className="text-xs uppercase tracking-wide text-nn-gray dark:text-slate-400">
          {t('auth.email')}
        </dt>
        <dd className="mt-1 text-sm font-medium text-gray-900 dark:text-slate-100">
          {user?.email ?? '—'}
        </dd>
      </div>
      <div>
        <dt className="text-xs uppercase tracking-wide text-nn-gray dark:text-slate-400">
          {t('profile.roleLabel')}
        </dt>
        <dd className="mt-1 text-sm font-medium text-gray-900 dark:text-slate-100">
          {t(`roles.${role}`)}
        </dd>
      </div>
      <div>
        <dt className="text-xs uppercase tracking-wide text-nn-gray dark:text-slate-400">
          {t('profile.statusLabel')}
        </dt>
        <dd className="mt-1 text-sm font-medium text-gray-900 dark:text-slate-100">
          {user?.is_active === false ? t('profile.statusInactive') : t('profile.statusActive')}
        </dd>
      </div>
    </dl>
  );
}

function extractedEntityCount(entities) {
  if (Array.isArray(entities)) return entities.length;
  if (entities && typeof entities === 'object' && Array.isArray(entities.interests)) {
    return entities.interests.length;
  }
  return 0;
}

function interestsWarningMessage(warning, t) {
  if (warning === 'model_interest_extraction_unavailable') {
    return t('profile.interestsExtractionUnavailable');
  }
  if (warning === 'model_interest_extraction_failed') {
    return t('profile.interestsExtractionFailed');
  }
  if (warning === 'client_interest_extraction_fallback') {
    return t('profile.interestsExtractionFallback');
  }
  return warning;
}

function InterestsSummary({ interests, interestsText, extractedEntities, warnings, t }) {
  const trimmedText = interestsText?.trim() ?? '';
  const hasInterests = interests.length > 0;
  const hasText = trimmedText.length > 0;
  const entityCount = extractedEntityCount(extractedEntities);

  if (!hasInterests && !hasText) {
    return (
      <p className="text-sm text-nn-gray dark:text-slate-400">{t('profile.interestsEmpty')}</p>
    );
  }

  return (
    <div className="space-y-2">
      {hasText && (
        <p className="line-clamp-3 text-sm text-gray-700 dark:text-slate-300">{trimmedText}</p>
      )}
      {hasInterests && (
        <div className="flex max-h-16 flex-wrap gap-1.5 overflow-hidden">
          {interests.map((interest) => (
            <span
              key={`${interest.label}-${(interest.sourceTerms ?? interest.source_terms ?? []).join('-')}`}
              className="rounded-full bg-nn-blue-light px-2.5 py-0.5 text-xs font-medium text-nn-blue dark:bg-slate-800 dark:text-slate-200"
              title={(interest.sourceTerms ?? interest.source_terms ?? []).join(', ')}
            >
              {interest.label}
              {(interest.sourceTerms ?? interest.source_terms ?? []).length > 0
                ? `: ${(interest.sourceTerms ?? interest.source_terms ?? []).slice(0, 2).join(', ')}`
                : ''}
            </span>
          ))}
        </div>
      )}
      {entityCount > 0 && (
        <p className="text-xs text-nn-gray dark:text-slate-400">
          {t('profile.extractedEntities', { count: entityCount })}
        </p>
      )}
      {warnings?.length > 0 && (
        <div className="space-y-1">
          {warnings.map((warning) => (
            <p key={warning} className="text-xs text-amber-700 dark:text-amber-300">
              {interestsWarningMessage(warning, t)}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ProfilePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const user = useAuthStore((s) => s.user);
  const role = useAuthStore((s) => s.role);

  const [activeTab, setActiveTab] = useState('account');
  const [editingProfile, setEditingProfile] = useState(false);
  const [editingPassword, setEditingPassword] = useState(false);
  const [editingInterests, setEditingInterests] = useState(false);

  const [profileUsername, setProfileUsername] = useState('');
  const [profileEmail, setProfileEmail] = useState('');
  const [profilePassword, setProfilePassword] = useState('');
  const [profileFieldError, setProfileFieldError] = useState(null);
  const [profileSubmitError, setProfileSubmitError] = useState(null);
  const [profileSuccess, setProfileSuccess] = useState(false);
  const [profileSaving, setProfileSaving] = useState(false);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordFieldError, setPasswordFieldError] = useState(null);
  const [passwordSubmitError, setPasswordSubmitError] = useState(null);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [passwordSaving, setPasswordSaving] = useState(false);

  const [interestsText, setInterestsText] = useState('');
  const [interests, setInterests] = useState([]);
  const [extractedEntities, setExtractedEntities] = useState([]);
  const [interestsBaseline, setInterestsBaseline] = useState(null);
  const [interestsWarnings, setInterestsWarnings] = useState([]);
  const [interestsLoading, setInterestsLoading] = useState(true);
  const [interestsSaving, setInterestsSaving] = useState(false);
  const [interestsSuccess, setInterestsSuccess] = useState(false);
  const [interestsError, setInterestsError] = useState(null);

  const [deactivatePassword, setDeactivatePassword] = useState('');
  const [securityError, setSecurityError] = useState(null);
  const [securityLoading, setSecurityLoading] = useState(false);

  const resetProfileForm = () => {
    setProfileUsername(user?.username ?? '');
    setProfileEmail(user?.email ?? '');
    setProfilePassword('');
    setProfileFieldError(null);
    setProfileSubmitError(null);
    setProfileSuccess(false);
  };

  const resetPasswordForm = () => {
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
    setPasswordFieldError(null);
    setPasswordSubmitError(null);
    setPasswordSuccess(false);
  };

  const resetInterestsForm = () => {
    const baseline = useMock ? loadUserInterests(user?.id) : interestsBaseline;
    if (baseline) {
      applyInterestsProfile(baseline);
    }
    setInterestsSuccess(false);
    setInterestsError(null);
  };

  const applyInterestsProfile = (profile) => {
    const normalized = {
      rawText: profile.rawText ?? '',
      interests: profile.interests ?? [],
      extractedEntities: profile.extractedEntities ?? [],
      warnings: profile.warnings ?? [],
    };
    setInterestsText(normalized.rawText);
    setInterests(normalized.interests);
    setExtractedEntities(normalized.extractedEntities);
    setInterestsWarnings(normalized.warnings);
    setInterestsBaseline(normalized);
  };

  const resetSecurityForm = () => {
    setDeactivatePassword('');
    setSecurityError(null);
  };

  const closeAllEditing = () => {
    setEditingProfile(false);
    setEditingPassword(false);
    setEditingInterests(false);
  };

  const handleTabChange = (tab) => {
    closeAllEditing();
    resetProfileForm();
    resetPasswordForm();
    resetInterestsForm();
    resetSecurityForm();
    setActiveTab(tab);
  };

  useEffect(() => {
    if (user) {
      setProfileUsername(user.username ?? '');
      setProfileEmail(user.email ?? '');
    }
  }, [user]);

  useEffect(() => {
    let active = true;
    if (!user?.id) {
      setInterestsLoading(false);
      return undefined;
    }

    setInterestsLoading(true);
    setInterestsError(null);
    loadInterestsProfile(user.id)
      .then((profile) => {
        if (active) applyInterestsProfile(profile);
      })
      .catch(() => {
        if (!active) return;
        if (useMock) {
          applyInterestsProfile(loadUserInterests(user.id));
        } else {
          setInterestsError('interests_load_failed');
        }
      })
      .finally(() => {
        if (active) setInterestsLoading(false);
      });

    return () => {
      active = false;
    };
  }, [user?.id]);

  const handleProfileSubmit = async (event) => {
    event.preventDefault();
    setProfileFieldError(null);
    setProfileSubmitError(null);
    setProfileSuccess(false);

    const validationError = validateProfileUpdateForm({
      username: profileUsername,
      email: profileEmail,
      currentUsername: user?.username ?? '',
      currentEmail: user?.email ?? '',
      currentPassword: profilePassword,
    });
    if (validationError) {
      setProfileFieldError(validationError);
      return;
    }

    const payload = { currentPassword: profilePassword };
    if (profileUsername.trim() !== (user?.username ?? '')) {
      payload.username = profileUsername.trim();
    }
    if (profileEmail.trim() !== (user?.email ?? '')) {
      payload.email = profileEmail.trim();
    }

    setProfileSaving(true);
    try {
      await updateProfile(payload);
      setProfilePassword('');
      setProfileSuccess(true);
      setEditingProfile(false);
    } catch (error) {
      setProfileSubmitError(mapAuthError(error));
    } finally {
      setProfileSaving(false);
    }
  };

  const handlePasswordSubmit = async (event) => {
    event.preventDefault();
    setPasswordFieldError(null);
    setPasswordSubmitError(null);
    setPasswordSuccess(false);

    const validationError = validatePasswordChangeForm({
      currentPassword,
      newPassword,
      confirmPassword,
    });
    if (validationError) {
      setPasswordFieldError(validationError);
      return;
    }

    setPasswordSaving(true);
    try {
      await changePassword({ currentPassword, newPassword });
      resetPasswordForm();
      setPasswordSuccess(true);
      setEditingPassword(false);
    } catch (error) {
      setPasswordSubmitError(mapAuthError(error));
    } finally {
      setPasswordSaving(false);
    }
  };

  const handleInterestsSave = async () => {
    const trimmed = interestsText.trim();
    if (!trimmed) return;
    setInterestsSaving(true);
    setInterestsSuccess(false);
    setInterestsError(null);
    try {
      const profile = await saveInterestsProfile(user?.id, trimmed);
      applyInterestsProfile(profile);
      setInterestsSuccess(true);
      setEditingInterests(false);
    } catch (error) {
      setInterestsError(error?.message ?? 'interests_save_failed');
    } finally {
      setInterestsSaving(false);
    }
  };

  const handleLogout = async () => {
    setSecurityError(null);
    setSecurityLoading(true);
    try {
      await logout();
    } catch (error) {
      setSecurityError(mapAuthError(error));
    } finally {
      setSecurityLoading(false);
      navigate('/login', { replace: true });
    }
  };

  const handleLogoutAll = async () => {
    if (!window.confirm(t('profile.confirmLogoutAll'))) return;
    setSecurityError(null);
    setSecurityLoading(true);
    try {
      await logoutAll();
    } catch (error) {
      setSecurityError(mapAuthError(error));
    } finally {
      setSecurityLoading(false);
      navigate('/login', { replace: true });
    }
  };

  const handleDeactivate = async () => {
    if (!deactivatePassword) {
      setSecurityError('passwordRequired');
      return;
    }
    if (!window.confirm(t('profile.confirmDeactivate'))) return;
    setSecurityError(null);
    setSecurityLoading(true);
    try {
      await deactivateAccount(deactivatePassword);
      navigate('/login', { replace: true });
    } catch (error) {
      setSecurityError(mapAuthError(error));
    } finally {
      setSecurityLoading(false);
    }
  };

  if (!user) {
    return (
      <PageShell title={t('profile.title')} hideHeading>
        <Loader />
      </PageShell>
    );
  }

  return (
    <PageShell title={t('profile.title')} hideHeading>
      <div className="flex h-full min-h-0 flex-col">
        <ProfileTabs activeTab={activeTab} onChange={handleTabChange} />
        <div className="min-h-0 flex-1 overflow-hidden pt-3" role="tabpanel">
          {activeTab === 'account' && (
            <div className="flex h-full min-h-0 flex-col gap-3">
              <ProfileSection
                compact
                className="shrink-0"
                editing={editingProfile}
                onEdit={() => setEditingProfile(true)}
                onCancel={() => {
                  resetProfileForm();
                  setEditingProfile(false);
                }}
                summary={<AccountSummary user={user} role={role} t={t} />}
              >
                <form onSubmit={handleProfileSubmit} className="space-y-3">
                  <div className="grid gap-3 sm:grid-cols-2">
                    <label className="block space-y-1">
                      <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
                        {t('auth.username')}
                      </span>
                      <input
                        type="text"
                        autoComplete="username"
                        value={profileUsername}
                        onChange={(event) => setProfileUsername(event.target.value)}
                        className={authInputClassName}
                        disabled={profileSaving}
                      />
                    </label>
                    <label className="block space-y-1">
                      <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
                        {t('auth.email')}
                      </span>
                      <input
                        type="email"
                        autoComplete="email"
                        value={profileEmail}
                        onChange={(event) => setProfileEmail(event.target.value)}
                        className={authInputClassName}
                        disabled={profileSaving}
                      />
                    </label>
                  </div>
                  <label className="block space-y-1">
                    <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
                      {t('profile.currentPassword')}
                    </span>
                    <input
                      type="password"
                      autoComplete="current-password"
                      value={profilePassword}
                      onChange={(event) => setProfilePassword(event.target.value)}
                      className={authInputClassName}
                      disabled={profileSaving}
                    />
                  </label>
                  {profileFieldError && (
                    <p className="text-sm text-red-600 dark:text-red-400" role="alert">
                      {t(`auth.errors.${profileFieldError}`)}
                    </p>
                  )}
                  {profileSubmitError && (
                    <p className="text-sm text-red-600 dark:text-red-400" role="alert">
                      {t(`auth.errors.${profileSubmitError}`, { defaultValue: t('auth.errors.unknown') })}
                    </p>
                  )}
                  {profileSuccess && (
                    <p className="text-sm text-green-700 dark:text-green-400" role="status">
                      {t('profile.saved')}
                    </p>
                  )}
                  <button type="submit" disabled={profileSaving} className={authSubmitClassName}>
                    {profileSaving ? t('profile.saving') : t('profile.saveChanges')}
                  </button>
                </form>
              </ProfileSection>

              <ProfileSection
                compact
                className="min-h-0 flex-1"
                title={t('profile.interestsTitle')}
                editing={editingInterests}
                onEdit={() => setEditingInterests(true)}
                onCancel={() => {
                  resetInterestsForm();
                  setEditingInterests(false);
                }}
                summary={
                  interestsLoading ? (
                    <p className="text-sm text-nn-gray dark:text-slate-400">{t('profile.interestsLoading')}</p>
                  ) : (
                    <InterestsSummary
                      interests={interests}
                      interestsText={interestsText}
                      extractedEntities={extractedEntities}
                      warnings={interestsWarnings}
                      t={t}
                    />
                  )
                }
              >
                <div className="space-y-3">
                  <textarea
                    value={interestsText}
                    onChange={(event) => setInterestsText(event.target.value)}
                    placeholder={t('profile.interestsPlaceholder')}
                    rows={3}
                    className={`${authInputClassName} resize-none`}
                    disabled={interestsSaving}
                  />
                  {interestsSuccess && (
                    <p className="text-sm text-green-700 dark:text-green-400" role="status">
                      {t('profile.interestsSaved')}
                    </p>
                  )}
                  {interestsError && (
                    <p className="text-sm text-red-600 dark:text-red-400" role="alert">
                      {t(`profile.errors.${interestsError}`, { defaultValue: interestsError })}
                    </p>
                  )}
                  {interestsWarnings.length > 0 && (
                    <div className="space-y-1">
                      {interestsWarnings.map((warning) => (
                        <p key={warning} className="text-xs text-amber-700 dark:text-amber-300">
                          {interestsWarningMessage(warning, t)}
                        </p>
                      ))}
                    </div>
                  )}
                  <button
                    type="button"
                    onClick={handleInterestsSave}
                    disabled={interestsSaving || !interestsText.trim()}
                    className={authSubmitClassName}
                  >
                    {interestsSaving ? t('profile.saving') : t('profile.saveInterests')}
                  </button>
                </div>
              </ProfileSection>
            </div>
          )}

          {activeTab === 'password' && (
            <ProfileSection
              compact
              className="h-full"
              editing={editingPassword}
              onEdit={() => setEditingPassword(true)}
              onCancel={() => {
                resetPasswordForm();
                setEditingPassword(false);
              }}
              summary={
                <p className="text-sm text-nn-gray dark:text-slate-400">
                  {t('profile.passwordMasked')}
                </p>
              }
            >
              <form onSubmit={handlePasswordSubmit} className="space-y-4">
                <label className="block space-y-1.5">
                  <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
                    {t('profile.currentPassword')}
                  </span>
                  <input
                    type="password"
                    autoComplete="current-password"
                    value={currentPassword}
                    onChange={(event) => setCurrentPassword(event.target.value)}
                    className={authInputClassName}
                    disabled={passwordSaving}
                  />
                </label>
                <label className="block space-y-1.5">
                  <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
                    {t('profile.newPassword')}
                  </span>
                  <input
                    type="password"
                    autoComplete="new-password"
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    className={authInputClassName}
                    disabled={passwordSaving}
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
                    className={authInputClassName}
                    disabled={passwordSaving}
                  />
                </label>
                <p className="text-xs text-nn-gray dark:text-slate-400">{t('auth.passwordHint')}</p>
                {passwordFieldError && (
                  <p className="text-sm text-red-600 dark:text-red-400" role="alert">
                    {t(`auth.errors.${passwordFieldError}`)}
                  </p>
                )}
                {passwordSubmitError && (
                  <p className="text-sm text-red-600 dark:text-red-400" role="alert">
                    {t(`auth.errors.${passwordSubmitError}`, { defaultValue: t('auth.errors.unknown') })}
                  </p>
                )}
                {passwordSuccess && (
                  <p className="text-sm text-green-700 dark:text-green-400" role="status">
                    {t('profile.passwordChanged')}
                  </p>
                )}
                <button type="submit" disabled={passwordSaving} className={authSubmitClassName}>
                  {passwordSaving ? t('profile.saving') : t('profile.changePassword')}
                </button>
              </form>
            </ProfileSection>
          )}

          {activeTab === 'security' && (
            <ProfileSection
              compact
              className="h-full"
              editable={false}
              title={t('profile.securityTitle')}
              danger
            >
              <div className="space-y-4">
                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    onClick={handleLogout}
                    disabled={securityLoading}
                    className={outlineButtonClassName}
                  >
                    {t('profile.logout')}
                  </button>
                  <button
                    type="button"
                    onClick={handleLogoutAll}
                    disabled={securityLoading}
                    className={outlineButtonClassName}
                  >
                    {t('profile.logoutAll')}
                  </button>
                </div>
                <div className="space-y-3 border-t border-red-200 pt-4 dark:border-red-900/50">
                  <p className="text-sm font-medium text-red-800 dark:text-red-300">
                    {t('profile.deactivateTitle')}
                  </p>
                  <label className="block space-y-1.5">
                    <span className="text-sm text-gray-700 dark:text-slate-300">
                      {t('profile.currentPassword')}
                    </span>
                    <input
                      type="password"
                      autoComplete="current-password"
                      value={deactivatePassword}
                      onChange={(event) => setDeactivatePassword(event.target.value)}
                      className={authInputClassName}
                      disabled={securityLoading}
                    />
                  </label>
                  <button
                    type="button"
                    onClick={handleDeactivate}
                    disabled={securityLoading}
                    className={dangerButtonClassName}
                  >
                    {t('profile.deactivate')}
                  </button>
                </div>
                {securityError && (
                  <p className="text-sm text-red-600 dark:text-red-400" role="alert">
                    {t(`auth.errors.${securityError}`, { defaultValue: t('auth.errors.unknown') })}
                  </p>
                )}
              </div>
            </ProfileSection>
          )}
        </div>
      </div>
    </PageShell>
  );
}
