function Header({ currentPage, onNavigate }) {
  const menuItems = [
    { id: "home", label: "Home" },
    { id: "create", label: "Create Lab" },
    { id: "session", label: "Session Detail" },
    { id: "result", label: "Validation Result" }
  ];

  return (
    <header className="header">
      <div className="logo-area">
        <h1>AutoNetLab</h1>
        <p>Intelligent Automated Network Training Laboratory</p>
      </div>

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
    </header>
  );
}

export default Header;