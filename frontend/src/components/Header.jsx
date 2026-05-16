import { useLanguage } from "../hooks/useLanguage";

function getRoleLabel(role) {
  return role === "instructor" ? "Instructor" : "Student";
}

function Header({ currentPage, onNavigate, authUser, onLogout }) {
  const { t } = useLanguage();

  const studentMenuItems = [
    { id: "home", label: t("navHome") },
    { id: "create", label: t("navCreateLab") },
    { id: "myLabs", label: "My Labs" },
    { id: "session", label: t("navSessionDetail") },
    { id: "result", label: t("navValidationResult") }
  ];

  const instructorMenuItems = [
    { id: "instructor", label: "Instructor Dashboard" }
  ];

  const menuItems =
    authUser?.role === "instructor" ? instructorMenuItems : studentMenuItems;

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

        {authUser && (
          <div className="auth-header-panel">
            <div>
              <span className="muted">Signed in as</span>
              <strong>{authUser.display_name || authUser.username}</strong>
            </div>

            <span className="auth-role-pill">
              {getRoleLabel(authUser.role)}
            </span>

            <button className="secondary-button" onClick={onLogout}>
              Logout
            </button>
          </div>
        )}
      </div>
    </header>
  );
}

export default Header;
