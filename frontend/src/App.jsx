import { useEffect, useState } from "react";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import CreateLab from "./pages/CreateLab";
import SessionDetail from "./pages/SessionDetail";
import ValidationResult from "./pages/ValidationResult";
import { getLab, isMockApiEnabled } from "./services/apiService";

function App() {
  const [currentPage, setCurrentPage] = useState("home");
  const [labSession, setLabSession] = useState(null);

  useEffect(() => {
  async function loadInitialData() {
    if (!isMockApiEnabled()) {
      return;
    }

    const labData = await getLab("lab-demo-001");
    setLabSession(labData);
  }

  loadInitialData();
}, []);

  function handleLabCreated(newLabSession) {
    setLabSession(newLabSession);
    setCurrentPage("session");
  }

  return (
    <Layout currentPage={currentPage} onNavigate={setCurrentPage}>
      {currentPage === "home" && (
        <Home labSession={labSession} onNavigate={setCurrentPage} />
      )}

      {currentPage === "create" && (
        <CreateLab
          onLabCreated={handleLabCreated}
          onNavigate={setCurrentPage}
        />
      )}

      {currentPage === "session" && (
        <SessionDetail
          labSession={labSession}
          onNavigate={setCurrentPage}
        />
      )}

      {currentPage === "result" && (
        <ValidationResult labSession={labSession} />
      )}
    </Layout>
  );
}

export default App;