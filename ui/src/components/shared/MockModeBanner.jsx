import { useTranslation } from 'react-i18next';
import { useMock } from '../../api/client.js';
import { DegradedBanner } from './PageState.jsx';

export default function MockModeBanner() {
  const { t } = useTranslation();

  if (!useMock) {
    return null;
  }

  return <DegradedBanner message={t('common.mockModeActive')} className="rounded-none" />;
}
