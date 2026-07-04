import React from 'react';
import { Navigate } from 'react-router-dom';
import AuthLayout from '../layout/AuthLayout.jsx';
import DashboardLayout from '../layout/DashboardLayout.jsx';
import ChatPage from '../pages/ChatPage.jsx';
import GraphPage from '../pages/GraphPage.jsx';
import StrategicCoveragePage from '../pages/StrategicCoveragePage.jsx';
import StrategicQualityPage from '../pages/StrategicQualityPage.jsx';
import LabMatrixPage from '../pages/LabMatrixPage.jsx';
import LabInsightsPage from '../pages/LabInsightsPage.jsx';
import AdminPage from '../pages/AdminPage.jsx';
import AdminStatsPage from '../pages/AdminStatsPage.jsx';
import AdminAuditPage from '../pages/AdminAuditPage.jsx';
import UploadPage from '../pages/UploadPage.jsx';
import SearchPage from '../pages/SearchPage.jsx';
import RegisterPage from '../pages/RegisterPage.jsx';
import LoginPage from '../pages/LoginPage.jsx';
import ForgotPasswordPage from '../pages/ForgotPasswordPage.jsx';
import ProfilePage from '../pages/ProfilePage.jsx';
import ReviewConsolePage from '../pages/ReviewConsolePage.jsx';
import RoleRoute from '../components/shared/RoleRoute.jsx';
import ReviewConsoleGate from '../components/review/ReviewConsoleGate.jsx';

export const routes = [
  {
    element: <AuthLayout />,
    children: [
      { path: '/login', element: <LoginPage /> },
      { path: '/register', element: <RegisterPage /> },
      { path: '/forgot-password', element: <ForgotPasswordPage /> },
    ],
  },
  {
    element: <DashboardLayout />,
    children: [
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
        element: <Navigate to="/strategic/coverage" replace />,
      },
      {
        path: '/strategic/coverage',
        element: (
          <RoleRoute paths={['strategic']}>
            <StrategicCoveragePage />
          </RoleRoute>
        ),
      },
      {
        path: '/strategic/quality',
        element: (
          <RoleRoute paths={['strategic']}>
            <StrategicQualityPage />
          </RoleRoute>
        ),
      },
      {
        path: '/lab',
        element: <Navigate to="/lab/matrix" replace />,
      },
      {
        path: '/lab/matrix',
        element: (
          <RoleRoute paths={['lab']}>
            <LabMatrixPage />
          </RoleRoute>
        ),
      },
      {
        path: '/lab/insights',
        element: (
          <RoleRoute paths={['lab']}>
            <LabInsightsPage />
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
        path: '/admin/stats',
        element: (
          <RoleRoute paths={['admin']}>
            <AdminStatsPage />
          </RoleRoute>
        ),
      },
      {
        path: '/admin/audit',
        element: (
          <RoleRoute paths={['admin']}>
            <AdminAuditPage />
          </RoleRoute>
        ),
      },
      {
        path: '/upload',
        element: (
          <RoleRoute paths={['upload']}>
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
      {
        path: '/profile',
        element: (
          <RoleRoute paths={['profile']}>
            <ProfilePage />
          </RoleRoute>
        ),
      },
      {
        path: '/review',
        element: (
          <ReviewConsoleGate>
            <RoleRoute paths={['review']}>
              <ReviewConsolePage />
            </RoleRoute>
          </ReviewConsoleGate>
        ),
      },
      { path: '*', element: <Navigate to="/chat" replace /> },
    ],
  },
];
