import { useMemo } from "react";
import { translations } from "../i18n/translations";
import { LanguageContext } from "./languageContextCore";

export function LanguageProvider({ children }) {
  const language = "en";

  const value = useMemo(() => {
    function t(key) {
      return translations.en[key] || key;
    }

    return {
      language,
      setLanguage: () => {},
      t
    };
  }, []);

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}