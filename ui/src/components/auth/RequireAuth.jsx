import { useEffect, useState } from 'react';
import { Navigate, Outlet, useLocation } from 'react-router-dom';
import { ensureAuth, restoreLiveSession } from '../../api/auth.js';
import { useMock } from '../../api/client.js';
import { useAuthStore } from '../../stores/authStore.js';
import Loader from '../shared/Loader.jsx';

export default function RequireAuth() {
  const location = useLocation();
  const [status, setStatus] = useState('loading');

  useEffect(() => {
    let cancelled = false;

    async function bootstrap() {
      try {
        if (useMock) {
          await ensureAuth();
        } else {
          await restoreLiveSession();
        }
        if (!cancelled) {
          setStatus('ready');
        }
      } catch {
        useAuthStore.getState().clearAuth();
        if (!cancelled) {
          setStatus('unauthenticated');
        }
      }
    }

    bootstrap();
    return () => {
      cancelled = true;
    };
  }, []);

  if (status === 'loading') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-nn-gray-light dark:bg-slate-950">
        <Loader />
      </div>
    );
  }

  if (status === 'unauthenticated') {
    const returnUrl = encodeURIComponent(`${location.pathname}${location.search}`);
    return <Navigate to={`/login?returnUrl=${returnUrl}`} replace />;
  }

  return <Outlet />;
}
