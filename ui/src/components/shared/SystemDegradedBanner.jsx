import { useTranslation } from 'react-i18next';
import { useMock } from '../../api/client.js';
import { useHealthStore } from '../../stores/healthStore.js';
import { DegradedBanner } from './PageState.jsx';

export default function SystemDegradedBanner() {
  const { t } = useTranslation();
  const overall = useHealthStore((state) => state.overall);
  const error = useHealthStore((state) => state.error);

  if (useMock) {
    return null;
  }
  if (overall !== 'degraded' && overall !== 'down' && !error) {
    return null;
  }

  const message = error ? t('health.degradedBannerError') : t('health.degradedBanner');
  return <DegradedBanner message={message} className="mx-3 mt-2 sm:mx-4 md:mx-6" />;
}
