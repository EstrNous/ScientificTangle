import { useRoutes } from 'react-router-dom';
import ErrorBoundary from '../components/shared/ErrorBoundary.jsx';
import { SourceDocumentProvider } from '../context/SourceDocumentContext.jsx';
import { routes } from './routes.jsx';

export default function App() {
  const element = useRoutes(routes);

  return (
    <ErrorBoundary>
      <SourceDocumentProvider>{element}</SourceDocumentProvider>
    </ErrorBoundary>
  );
}
