import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import { startHealthPolling } from '../stores/healthStore.js';
import DashboardShell from './DashboardShell.jsx';

export default function DashboardLayout() {
  useEffect(() => {
    const stopHealthPolling = startHealthPolling();
    return stopHealthPolling;
  }, []);

  return (
    <DashboardShell>
      <Outlet />
    </DashboardShell>
  );
}
