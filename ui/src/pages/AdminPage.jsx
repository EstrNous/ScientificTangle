import { useEffect, useMemo, useState } from 'react';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import {
  AdminSummaryCards,
  AccessPolicyTable,
  AuditLogTable,
  OpsMetricsCards,
  ServiceMetricsTable,
  SourceViewer,
  UserRoleTable,
} from '../components/admin/index.js';
import { apiGet } from '../api/client.js';

export default function AdminPage() {
  const [loading, setLoading] = useState(true);
  const [adminData, setAdminData] = useState(null);
  const [auditEvents, setAuditEvents] = useState([]);
  const [users, setUsers] = useState([]);
  const [selectedEventId, setSelectedEventId] = useState(null);

  useEffect(() => {
    Promise.all([apiGet('/admin'), apiGet('/audit/events')])
      .then(([admin, events]) => {
        setAdminData(admin);
        setUsers(admin.users ?? []);
        setAuditEvents(events);
        const withSource = events.find((event) => event.source_span_id);
        setSelectedEventId(withSource?.id ?? events[0]?.id ?? null);
      })
      .finally(() => setLoading(false));
  }, []);

  const selectedSpan = useMemo(() => {
    const event = auditEvents.find((item) => item.id === selectedEventId);
    if (!event?.source_span_id) return null;
    return adminData?.source_spans?.[event.source_span_id] ?? null;
  }, [auditEvents, selectedEventId, adminData]);

  const handleRoleChange = (userId, role) => {
    setUsers((prev) => prev.map((user) => (user.id === userId ? { ...user, role } : user)));
  };

  const handleActiveToggle = (userId) => {
    setUsers((prev) =>
      prev.map((user) => (user.id === userId ? { ...user, active: !user.active } : user)),
    );
  };

  if (loading) return <Loader />;

  return (
    <PageShell>
      <div className="flex h-full min-h-0 flex-col gap-6 overflow-y-auto pr-1">
        <AdminSummaryCards summary={adminData?.summary} />
        <OpsMetricsCards operations={adminData?.operations} />
        <ServiceMetricsTable services={adminData?.operations?.services} />
        <div className="grid gap-4 xl:grid-cols-2">
          <UserRoleTable
            users={users}
            onRoleChange={handleRoleChange}
            onActiveToggle={handleActiveToggle}
          />
          <AccessPolicyTable policies={adminData?.access_policies} />
        </div>
        <div className="grid min-h-0 gap-4 xl:grid-cols-[1fr_320px]">
          <AuditLogTable
            events={auditEvents}
            selectedId={selectedEventId}
            onSelect={(event) => setSelectedEventId(event.id)}
          />
          <SourceViewer span={selectedSpan} />
        </div>
      </div>
    </PageShell>
  );
}
