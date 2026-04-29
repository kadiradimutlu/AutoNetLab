import { useMemo, useState } from "react";
import { translations } from "../i18n/translations";
import { LanguageContext } from "./languageContextCore";

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState("en");

  const value = useMemo(() => {
    function t(key) {
      return translations[language][key] || key;
    }

    return {
      language,
      setLanguage,
      t
    };
  }, [language]);

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}