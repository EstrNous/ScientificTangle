import { Outlet } from 'react-router-dom';
import DashboardShell from './DashboardShell.jsx';

export default function DashboardLayout() {
  return (
    <DashboardShell>
      <Outlet />
    </DashboardShell>
  );
}
