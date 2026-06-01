import Header from "./Header";
import BackToTopButton from "./BackToTopButton";

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
      <BackToTopButton />
    </div>
  );
}

export default Layout;
