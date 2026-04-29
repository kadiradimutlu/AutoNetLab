import Header from "./Header";

function Layout({ currentPage, onNavigate, children }) {
  return (
    <div className="app-shell">
      <Header currentPage={currentPage} onNavigate={onNavigate} />
      <main className="page">{children}</main>
    </div>
  );
}

export default Layout;