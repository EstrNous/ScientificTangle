import { Navigate } from 'react-router-dom';
import { isReviewConsoleEnabled } from '../../utils/uiFeatureFlags.js';

export default function ReviewConsoleGate({ children }) {
  if (!isReviewConsoleEnabled()) {
    return <Navigate to="/chat" replace />;
  }
  return children;
}
