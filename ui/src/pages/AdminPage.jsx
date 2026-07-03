import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import { AccessPolicyTable, AdminSubNav, UserRoleTable } from '../components/admin/index.js';
import PdfDownloadButton from '../components/shared/PdfDownloadButton.jsx';
import { apiGet } from '../api/client.js';
import { captureElementImage, waitForPaint } from '../utils/captureElement.js';
import { exportAdminManagementPdf } from '../utils/pagePdfExport.js';

const PANELS = {
  USERS: 'users',
  ACCESS: 'access',
};

export default function AdminPage() {
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [adminData, setAdminData] = useState(null);
  const [users, setUsers] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [expandedPanel, setExpandedPanel] = useState(null);
  const exportRef = useRef(null);

  useEffect(() => {
    apiGet('/admin')
      .then((admin) => {
        setAdminData(admin);
        setUsers(admin.users ?? []);
        setPolicies(admin.access_policies ?? []);
      })
      .finally(() => setLoading(false));
  }, []);

  const handleRoleChange = (userId, role) => {
    setUsers((prev) => prev.map((user) => (user.id === userId ? { ...user, role } : user)));
  };

  const handleActiveToggle = (userId) => {
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
    setPolicies((prev) =>
      prev.map((policy) => (policy.id === policyId ? { ...policy, level } : policy)),
    );
  };

  const handlePolicyExportToggle = (policyId) => {
    setPolicies((prev) =>
      prev.map((policy) =>
        policy.id === policyId ? { ...policy, export_allowed: !policy.export_allowed } : policy,
      ),
    );
  };

  const handlePolicyRoleToggle = (policyId, role) => {
    setPolicies((prev) =>
      prev.map((policy) => {
        if (policy.id !== policyId) return policy;
        const roles = policy.roles.includes(role)
          ? policy.roles.filter((item) => item !== role)
          : [...policy.roles, role];
        return { ...policy, roles };
      }),
    );
  };

  const togglePanel = (panel) => {
    setExpandedPanel((prev) => (prev === panel ? null : panel));
  };

  const isPanelVisible = (panel) => !expandedPanel || expandedPanel === panel;
  const isPanelExpanded = (panel) => expandedPanel === panel;

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
        <AdminSubNav action={<PdfDownloadButton onExport={handleExportPdf} />} />

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
              expanded={isPanelExpanded(PANELS.ACCESS)}
              onToggleExpand={() => togglePanel(PANELS.ACCESS)}
            />
          )}
        </div>
      </div>
    </PageShell>
  );
}
