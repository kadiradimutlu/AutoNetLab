import Header from "./Header";

function Layout({ currentPage, onNavigate, authUser, onLogout, children }) {
  return (
    <div className="app-shell">
      <Header
        currentPage={currentPage}
        onNavigate={onNavigate}
        authUser={authUser}
        onLogout={onLogout}
      />
      <main className="page">{children}</main>
    </div>
  );
}

export default Layout;
