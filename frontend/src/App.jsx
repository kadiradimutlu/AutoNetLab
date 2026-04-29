import { useEffect, useState } from "react";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import CreateLab from "./pages/CreateLab";
import SessionDetail from "./pages/SessionDetail";
import ValidationResult from "./pages/ValidationResult";
import { getSession, getTopology } from "./services/apiService";

function App() {
  const [currentPage, setCurrentPage] = useState("home");
  const [session, setSession] = useState(null);
  const [topology, setTopology] = useState(null);

  useEffect(() => {
    async function loadInitialData() {
      const sessionData = await getSession("sess-001");
      const topologyData = await getTopology(sessionData.topologyId);

      setSession(sessionData);
      setTopology(topologyData);
    }

    loadInitialData();
  }, []);

  function handleSessionCreated(newSession) {
    setSession(newSession);
    setCurrentPage("session");
  }

  return (
    <Layout currentPage={currentPage} onNavigate={setCurrentPage}>
      {currentPage === "home" && (
        <Home session={session} onNavigate={setCurrentPage} />
      )}

      {currentPage === "create" && (
        <CreateLab
          onSessionCreated={handleSessionCreated}
          onNavigate={setCurrentPage}
        />
      )}

      {currentPage === "session" && (
        <SessionDetail
          session={session}
          topology={topology}
          onNavigate={setCurrentPage}
        />
      )}

      {currentPage === "result" && (
        <ValidationResult session={session} />
      )}
    </Layout>
  );
}

export default App;