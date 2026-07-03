import { Navigate } from 'react-router-dom';
import ChatPage from '../pages/ChatPage.jsx';
import GraphPage from '../pages/GraphPage.jsx';
import StrategicPage from '../pages/StrategicPage.jsx';
import LabPage from '../pages/LabPage.jsx';
import AdminPage from '../pages/AdminPage.jsx';
import UploadPage from '../pages/UploadPage.jsx';
import SearchPage from '../pages/SearchPage.jsx';
import RoleRoute from '../components/shared/RoleRoute.jsx';

export const routes = [
  { path: '/', element: <Navigate to="/chat" replace /> },
  {
    path: '/chat',
    element: (
      <RoleRoute paths={['chat']}>
        <ChatPage />
      </RoleRoute>
    ),
  },
  {
    path: '/graph',
    element: (
      <RoleRoute paths={['graph']}>
        <GraphPage />
      </RoleRoute>
    ),
  },
  {
    path: '/strategic',
    element: (
      <RoleRoute paths={['strategic']}>
        <StrategicPage />
      </RoleRoute>
    ),
  },
  {
    path: '/lab',
    element: (
      <RoleRoute paths={['lab']}>
        <LabPage />
      </RoleRoute>
    ),
  },
  {
    path: '/admin',
    element: (
      <RoleRoute paths={['admin']}>
        <AdminPage />
      </RoleRoute>
    ),
  },
  {
    path: '/upload',
    element: (
      <RoleRoute paths={['graph', 'upload']}>
        <UploadPage />
      </RoleRoute>
    ),
  },
  {
    path: '/search',
    element: (
      <RoleRoute paths={['lab', 'search']}>
        <SearchPage />
      </RoleRoute>
    ),
  },
  { path: '*', element: <Navigate to="/chat" replace /> },
];
