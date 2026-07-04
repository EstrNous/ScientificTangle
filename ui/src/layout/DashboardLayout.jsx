import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { fetchCurrentUser } from '../api/auth.js';
import { useMock } from '../api/client.js';
import { startHealthPolling } from '../stores/healthStore.js';
import DashboardShell from './DashboardShell.jsx';

export default function DashboardLayout() {
  useEffect(() => {
    const stopHealthPolling = startHealthPolling();
    if (useMock) {
      return stopHealthPolling;
    }
    fetchCurrentUser().catch(() => {});
    return stopHealthPolling;
  }, []);

  return (
    <DashboardShell>
      <Outlet />
    </DashboardShell>
  );
}
