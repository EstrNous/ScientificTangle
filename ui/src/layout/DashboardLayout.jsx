import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { fetchCurrentUser } from '../api/auth.js';
import { useMock } from '../api/client.js';
import DashboardShell from './DashboardShell.jsx';

export default function DashboardLayout() {
  useEffect(() => {
    if (useMock) return undefined;
    fetchCurrentUser().catch(() => {});
    return undefined;
  }, []);

  return (
    <DashboardShell>
      <Outlet />
    </DashboardShell>
  );
}
