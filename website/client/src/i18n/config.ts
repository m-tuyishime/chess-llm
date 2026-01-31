import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './locales/en.json';
import fr from './locales/fr.json';

// Get language from localStorage or navigator
const getInitialLanguage = () => {
  const stored = localStorage.getItem('lang');
  if (stored) {
    try {
      // Handle both JSON-encoded and raw strings
      return JSON.parse(stored);
    } catch {
      return stored;
    }
  }
  return navigator.language.startsWith('fr') ? 'fr' : 'en';
};

i18n.use(initReactI18next).init({
  resources: {
    en: { translation: en },
    fr: { translation: fr },
  },
  lng: getInitialLanguage(),
  fallbackLng: 'en',
  interpolation: {
    escapeValue: false, // react already safes from xss
  },
  react: {
    useSuspense: false,
  },
});

export default i18n;
