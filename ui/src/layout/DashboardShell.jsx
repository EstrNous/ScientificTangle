import TopBar from './TopBar.jsx';
import TabNav from './TabNav.jsx';

export default function DashboardShell({ children }) {
  return (
    <div className="flex h-screen flex-col overflow-hidden bg-nn-gray-light text-gray-900 dark:bg-slate-950 dark:text-slate-100">
      <TopBar />
      <TabNav />
      <main className="min-h-0 flex-1 overflow-hidden p-6">{children}</main>
    </div>
  );
}
