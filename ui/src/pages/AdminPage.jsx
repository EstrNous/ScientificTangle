import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import { AccessPolicyTable, AdminSubNav, UserRoleTable } from '../components/admin/index.js';
import PdfDownloadButton from '../components/shared/PdfDownloadButton.jsx';
import { apiGet } from '../api/client.js';
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
  const [expandedPanel, setExpandedPanel] = useState(null);

  useEffect(() => {
    apiGet('/admin')
      .then((admin) => {
        setAdminData(admin);
        setUsers(admin.users ?? []);
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

  const togglePanel = (panel) => {
    setExpandedPanel((prev) => (prev === panel ? null : panel));
  };

  const isPanelVisible = (panel) => !expandedPanel || expandedPanel === panel;
  const isPanelExpanded = (panel) => expandedPanel === panel;

  if (loading) return <Loader />;

  return (
    <PageShell>
      <div
        className={`flex h-full min-h-0 flex-col gap-6 ${
          expandedPanel ? 'overflow-hidden' : 'overflow-y-auto pr-1'
        }`}
      >
        <AdminSubNav
          action={
            <PdfDownloadButton
              onExport={() =>
                exportAdminManagementPdf({
                  users,
                  policies: adminData?.access_policies,
                  t,
                  language: i18n.language,
                })
              }
            />
          }
        />

        <div
          className={`grid gap-4 ${
            expandedPanel === PANELS.USERS || expandedPanel === PANELS.ACCESS
              ? 'min-h-0 flex-1'
              : 'xl:grid-cols-2'
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
              policies={adminData?.access_policies}
              expanded={isPanelExpanded(PANELS.ACCESS)}
              onToggleExpand={() => togglePanel(PANELS.ACCESS)}
            />
          )}
        </div>
      </div>
    </PageShell>
  );
}
