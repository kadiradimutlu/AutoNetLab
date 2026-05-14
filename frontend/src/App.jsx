import { useEffect, useState } from "react";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import CreateLab from "./pages/CreateLab";
import SessionDetail from "./pages/SessionDetail";
import ValidationResult from "./pages/ValidationResult";
import { getLab, isMockApiEnabled } from "./services/apiService";

const ACTIVE_SESSION_STORAGE_KEY = "autonetlab_active_session_id";

function App() {
  const [currentPage, setCurrentPage] = useState("home");
  const [labSession, setLabSession] = useState(null);

  useEffect(() => {
    async function loadInitialData() {
      try {
        if (isMockApiEnabled()) {
          const labData = await getLab("lab-demo-001");
          setLabSession(labData);
          return;
        }

        const savedSessionId = localStorage.getItem(ACTIVE_SESSION_STORAGE_KEY);

        if (!savedSessionId) {
          return;
        }

        const savedLabSession = await getLab(savedSessionId);
        setLabSession(savedLabSession);
        setCurrentPage("session");
      } catch (error) {
        console.error("Initial lab session could not be loaded.", error);
        localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
      }
    }

    loadInitialData();
  }, []);

  function handleLabCreated(newLabSession) {
    setLabSession(newLabSession);

    if (newLabSession?.session_id) {
      localStorage.setItem(
        ACTIVE_SESSION_STORAGE_KEY,
        newLabSession.session_id
      );
    }

    setCurrentPage("session");
  }

  function handleLabUpdated(updatedLabSession) {
    setLabSession(updatedLabSession);

    if (updatedLabSession?.session_id) {
      localStorage.setItem(
        ACTIVE_SESSION_STORAGE_KEY,
        updatedLabSession.session_id
      );
    }
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
          onLabUpdated={handleLabUpdated}
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