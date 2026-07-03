import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { I18nextProvider } from 'react-i18next';
import i18n from '../i18n/index.js';
import { useAuthStore } from '../stores/authStore.js';

export function renderWithProviders(ui, { route = '/', role } = {}) {
  if (role) {
    useAuthStore.setState({ role });
  }
  return render(
    <I18nextProvider i18n={i18n}>
      <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
    </I18nextProvider>,
  );
}
