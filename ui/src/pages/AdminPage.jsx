import { useEffect, useRef, useState } from 'react';

import { useTranslation } from 'react-i18next';

import PageShell from '../components/shared/PageShell.jsx';

import Loader from '../components/shared/Loader.jsx';

import { ErrorBanner } from '../components/shared/PageState.jsx';

import { AccessPolicyTable, AdminSubNav, DictionaryVersionTable, UserRoleTable } from '../components/admin/index.js';

import PdfDownloadButton from '../components/shared/PdfDownloadButton.jsx';

import { fetchAdminSnapshot, patchAdminPolicy, patchAdminUser } from '../api/admin.js';
import { activateDictionaryVersion, fetchDictionaryVersions } from '../api/dictionaries.js';

import { captureElementImage, waitForPaint } from '../utils/captureElement.js';

import { exportAdminManagementPdf } from '../utils/pagePdfExport.js';

import {

  buildAdminBaselines,

  isPolicyDirty,

  isUserDirty,

  listDirtyPolicyIds,

  listDirtyUserIds,

} from '../utils/adminDirtyState.js';



const PANELS = {

  USERS: 'users',

  ACCESS: 'access',

  DICTIONARIES: 'dictionaries',

};



export default function AdminPage() {

  const { t, i18n } = useTranslation();

  const [loading, setLoading] = useState(true);

  const [users, setUsers] = useState([]);

  const [policies, setPolicies] = useState([]);

  const [baselineUsers, setBaselineUsers] = useState([]);

  const [baselinePolicies, setBaselinePolicies] = useState([]);

  const [expandedPanel, setExpandedPanel] = useState(null);

  const [savingUserId, setSavingUserId] = useState(null);

  const [savingPolicyId, setSavingPolicyId] = useState(null);

  const [savingAll, setSavingAll] = useState(false);

  const [saveError, setSaveError] = useState(null);

  const [loadError, setLoadError] = useState(null);

  const [saveSuccess, setSaveSuccess] = useState(false);

  const [dictionaries, setDictionaries] = useState([]);

  const [dictionaryError, setDictionaryError] = useState(null);

  const [activatingDictionaryId, setActivatingDictionaryId] = useState(null);

  const exportRef = useRef(null);



  useEffect(() => {

    let cancelled = false;

    fetchAdminSnapshot()

      .then((admin) => {

        if (cancelled) return;

        setUsers(admin.users ?? []);

        setPolicies(admin.policies ?? []);

        const baselines = buildAdminBaselines(admin.users ?? [], admin.policies ?? []);

        setBaselineUsers(baselines.users);

        setBaselinePolicies(baselines.policies);

      })

      .catch((error) => {

        if (!cancelled) setLoadError(error?.message ?? 'admin_load_failed');

      })

      .finally(() => {

        if (!cancelled) setLoading(false);

      });

    fetchDictionaryVersions()

      .then((items) => {

        if (!cancelled) setDictionaries(items);

      })

      .catch((error) => {

        if (!cancelled) setDictionaryError(error?.message ?? 'dictionaries_load_failed');

      });

    return () => {

      cancelled = true;

    };

  }, []);



  const dirtyUserIds = listDirtyUserIds(users, baselineUsers);

  const dirtyPolicyIds = listDirtyPolicyIds(policies, baselinePolicies);

  const hasDirtyChanges = dirtyUserIds.length > 0 || dirtyPolicyIds.length > 0;



  const handleRoleChange = (userId, role) => {

    setSaveSuccess(false);

    setUsers((prev) => prev.map((user) => (user.id === userId ? { ...user, role } : user)));

  };



  const handleActiveToggle = (userId) => {

    setSaveSuccess(false);

    setUsers((prev) =>

      prev.map((user) => (user.id === userId ? { ...user, active: !user.active } : user)),

    );

  };



  const handleUserDelete = (userId) => {

    const user = users.find((item) => item.id === userId);

    if (!user) return;

    if (!window.confirm(t('admin.confirmDeleteUser', { name: user.name }))) return;

    setUsers((prev) => prev.filter((item) => item.id !== userId));

  };



  const handlePolicyLevelChange = (policyId, level) => {

    setSaveSuccess(false);

    setPolicies((prev) =>

      prev.map((policy) => (policy.id === policyId ? { ...policy, level } : policy)),

    );

  };



  const handlePolicyExportToggle = (policyId) => {

    setSaveSuccess(false);

    setPolicies((prev) =>

      prev.map((policy) =>

        policy.id === policyId ? { ...policy, exportAllowed: !policy.exportAllowed } : policy,

      ),

    );

  };



  const handlePolicyRoleToggle = (policyId, role) => {

    setSaveSuccess(false);

    setPolicies((prev) =>

      prev.map((policy) => {

        if (policy.id !== policyId) return policy;

        const currentRoles = policy.roles ?? [];

        const roles = currentRoles.includes(role)

          ? currentRoles.filter((item) => item !== role)

          : [...currentRoles, role];

        return { ...policy, roles };

      }),

    );

  };



  const refreshBaselines = (nextUsers, nextPolicies) => {

    const baselines = buildAdminBaselines(nextUsers, nextPolicies);

    setBaselineUsers(baselines.users);

    setBaselinePolicies(baselines.policies);

  };



  const handleSaveUser = async (userId) => {

    const user = users.find((item) => item.id === userId);

    if (!user || !isUserDirty(user, baselineUsers)) return;

    setSavingUserId(userId);

    setSaveError(null);

    setSaveSuccess(false);

    try {

      const saved = await patchAdminUser(userId, { role: user.role, active: user.active });

      const nextUsers = users.map((item) => (item.id === userId ? { ...item, ...saved } : item));

      setUsers(nextUsers);

      refreshBaselines(nextUsers, policies);

      setSaveSuccess(true);

    } catch (error) {

      setSaveError(error?.message ?? 'admin_user_save_failed');

    } finally {

      setSavingUserId(null);

    }

  };



  const handleSavePolicy = async (policyId) => {

    const policy = policies.find((item) => item.id === policyId);

    if (!policy || !isPolicyDirty(policy, baselinePolicies)) return;

    setSavingPolicyId(policyId);

    setSaveError(null);

    setSaveSuccess(false);

    try {

      const saved = await patchAdminPolicy(policy.documentId ?? policy.id, {

        level: policy.level,

        exportAllowed: policy.exportAllowed,

        roles: policy.roles,

      });

      const nextPolicies = policies.map((item) =>

        item.id === policyId ? { ...item, ...saved } : item,

      );

      setPolicies(nextPolicies);

      refreshBaselines(users, nextPolicies);

      setSaveSuccess(true);

    } catch (error) {

      setSaveError(error?.message ?? 'admin_policy_save_failed');

    } finally {

      setSavingPolicyId(null);

    }

  };



  const handleSaveAll = async () => {

    setSavingAll(true);

    setSaveError(null);

    setSaveSuccess(false);

    let nextUsers = users;

    let nextPolicies = policies;

    try {

      for (const userId of dirtyUserIds) {

        const user = nextUsers.find((item) => item.id === userId);

        if (!user) continue;

        const saved = await patchAdminUser(userId, { role: user.role, active: user.active });

        nextUsers = nextUsers.map((item) => (item.id === userId ? { ...item, ...saved } : item));

      }

      for (const policyId of dirtyPolicyIds) {

        const policy = nextPolicies.find((item) => item.id === policyId);

        if (!policy) continue;

        const saved = await patchAdminPolicy(policy.documentId ?? policy.id, {

          level: policy.level,

          exportAllowed: policy.exportAllowed,

          roles: policy.roles,

        });

        nextPolicies = nextPolicies.map((item) =>

          item.id === policyId ? { ...item, ...saved } : item,

        );

      }

      setUsers(nextUsers);

      setPolicies(nextPolicies);

      refreshBaselines(nextUsers, nextPolicies);

      setSaveSuccess(true);

    } catch (error) {

      setSaveError(error?.message ?? 'admin_save_failed');

    } finally {

      setSavingAll(false);

    }

  };



  const togglePanel = (panel) => {

    setExpandedPanel((prev) => (prev === panel ? null : panel));

  };



  const isPanelVisible = (panel) => !expandedPanel || expandedPanel === panel;

  const isPanelExpanded = (panel) => expandedPanel === panel;



  const handleActivateDictionary = async (versionId) => {

    setActivatingDictionaryId(versionId);

    setDictionaryError(null);

    try {

      const activated = await activateDictionaryVersion(versionId);

      setDictionaries((current) =>

        current.map((item) => ({

          ...item,

          status: item.id === activated.id ? activated.status : item.status === 'active' ? 'inactive' : item.status,

        })),

      );

    } catch (error) {

      setDictionaryError(error?.message ?? 'dictionary_activate_failed');

    } finally {

      setActivatingDictionaryId(null);

    }

  };



  const handleExportPdf = async () => {
    const wasExpanded = expandedPanel;

    if (wasExpanded) setExpandedPanel(null);

    await waitForPaint(200);

    const dashboardImage = await captureElementImage(exportRef.current, { fullContent: true });

    if (wasExpanded) setExpandedPanel(wasExpanded);

    await exportAdminManagementPdf({

      users,

      policies,

      t,

      language: i18n.language,

      dashboardImage,

    });

  };



  if (loading) return <Loader />;



  return (

    <PageShell>

      <div className="flex h-full min-h-0 flex-col gap-4 overflow-hidden">

        <AdminSubNav

          action={

            <div className="flex flex-wrap items-center gap-2">

              {hasDirtyChanges && (

                <button

                  type="button"

                  onClick={handleSaveAll}

                  disabled={savingAll}

                  className="rounded-lg bg-nn-blue px-3 py-1.5 text-xs font-medium text-white hover:bg-nn-blue/90 disabled:opacity-50"

                >

                  {savingAll ? t('admin.savingAll') : t('admin.saveAll', { count: dirtyUserIds.length + dirtyPolicyIds.length })}

                </button>

              )}

              <PdfDownloadButton onExport={handleExportPdf} />

            </div>

          }

        />

        {loadError && (
          <ErrorBanner message={t(`admin.errors.${loadError}`, { defaultValue: loadError })} />
        )}

        {saveError && (
          <ErrorBanner message={t(`admin.errors.${saveError}`, { defaultValue: saveError })} />
        )}

        {saveSuccess && !hasDirtyChanges && (

          <p className="text-sm text-green-700 dark:text-green-400" role="status">

            {t('admin.saved')}

          </p>

        )}

        {dictionaryError && (
          <ErrorBanner message={t(`admin.errors.${dictionaryError}`, { defaultValue: dictionaryError })} />
        )}



        <div

          ref={exportRef}

          className={`grid min-h-0 flex-1 gap-4 ${

            expandedPanel ? '' : 'xl:grid-cols-2'

          }`}

        >

          {isPanelVisible(PANELS.USERS) && (

            <UserRoleTable

              users={users}

              onRoleChange={handleRoleChange}

              onActiveToggle={handleActiveToggle}

              onDelete={handleUserDelete}

              onSave={handleSaveUser}

              dirtyUserIds={dirtyUserIds}

              savingUserId={savingUserId}

              expanded={isPanelExpanded(PANELS.USERS)}

              onToggleExpand={() => togglePanel(PANELS.USERS)}

            />

          )}

          {isPanelVisible(PANELS.ACCESS) && (

            <AccessPolicyTable

              policies={policies}

              onLevelChange={handlePolicyLevelChange}

              onRoleToggle={handlePolicyRoleToggle}

              onExportToggle={handlePolicyExportToggle}

              onSave={handleSavePolicy}

              dirtyPolicyIds={dirtyPolicyIds}

              savingPolicyId={savingPolicyId}

              expanded={isPanelExpanded(PANELS.ACCESS)}

              onToggleExpand={() => togglePanel(PANELS.ACCESS)}

            />

          )}

          {isPanelVisible(PANELS.DICTIONARIES) && (

            <DictionaryVersionTable

              versions={dictionaries}

              activatingId={activatingDictionaryId}

              onActivate={handleActivateDictionary}

              expanded={isPanelExpanded(PANELS.DICTIONARIES)}

              onToggleExpand={() => togglePanel(PANELS.DICTIONARIES)}

            />

          )}

        </div>

      </div>

    </PageShell>

  );

}
