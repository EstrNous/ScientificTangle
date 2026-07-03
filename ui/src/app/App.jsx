import { useRoutes } from 'react-router-dom';
import DashboardShell from '../layout/DashboardShell.jsx';
import ErrorBoundary from '../components/shared/ErrorBoundary.jsx';
import { SourceDocumentProvider } from '../context/SourceDocumentContext.jsx';
import { routes } from './routes.jsx';

export default function App() {
  const element = useRoutes(routes);

  return (
    <ErrorBoundary>
      <SourceDocumentProvider>
        <DashboardShell>{element}</DashboardShell>
      </SourceDocumentProvider>
    </ErrorBoundary>
  );
}
