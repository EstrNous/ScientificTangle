import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import ru from './ru.json';
import en from './en.json';

const defaultLocale = import.meta.env.VITE_DEFAULT_LOCALE || 'ru';

i18n.use(initReactI18next).init({
  resources: {
    ru: { translation: ru },
    en: { translation: en },
  },
  lng: defaultLocale,
  fallbackLng: 'ru',
  interpolation: { escapeValue: false },
});

export default i18n;
