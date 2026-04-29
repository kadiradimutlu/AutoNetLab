import { useLanguage } from "../hooks/useLanguage";

function Header({ currentPage, onNavigate }) {
  const { language, setLanguage, t } = useLanguage();

  const menuItems = [
    { id: "home", label: t("navHome") },
    { id: "create", label: t("navCreateLab") },
    { id: "session", label: t("navSessionDetail") },
    { id: "result", label: t("navValidationResult") }
  ];

  return (
    <header className="header">
      <div className="logo-area">
        <h1>AutoNetLab</h1>
        <p>{t("appSubtitle")}</p>
      </div>

      <div className="header-actions">
        <nav className="nav">
          {menuItems.map((item) => (
            <button
              key={item.id}
              className={currentPage === item.id ? "active" : ""}
              onClick={() => onNavigate(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="language-switch" aria-label={t("language")}>
          <button
            className={language === "en" ? "active" : ""}
            onClick={() => setLanguage("en")}
          >
            {t("english")}
          </button>

          <button
            className={language === "tr" ? "active" : ""}
            onClick={() => setLanguage("tr")}
          >
            {t("turkish")}
          </button>
        </div>
      </div>
    </header>
  );
}

export default Header;