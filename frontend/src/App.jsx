import { useEffect, useState } from "react";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import CreateLab from "./pages/CreateLab";
import SessionDetail from "./pages/SessionDetail";
import LabWorkspacePage from "./pages/LabWorkspacePage";
import ValidationResult from "./pages/ValidationResult";
import InstructorDashboardPage from "./pages/InstructorDashboardPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import MyLabsPage from "./pages/MyLabsPage";
import {
  getCurrentUser,
  getLab,
  isMockApiEnabled,
  logoutUser
} from "./services/apiService";
import { clearTerminalTranscriptsForSession } from "./utils/terminalTranscriptStorage";

const ACTIVE_SESSION_STORAGE_KEY = "autonetlab_active_session_id";

function getDefaultPageForRole(role) {
  return role === "instructor" ? "instructor" : "home";
}

function isInactiveLabStatus(status) {
  return ["finished", "destroyed"].includes(String(status || "").toLowerCase());
}

function scrollToPageTop() {
  if (typeof window === "undefined") {
    return;
  }

  window.requestAnimationFrame(() => {
    window.scrollTo({
      top: 0,
      left: 0,
      behavior: "auto"
    });
  });
}

function isPageAllowedForRole(page, role) {
  if (role === "instructor") {
    return page === "instructor";
  }

  if (role === "student") {
    return ["home", "create", "myLabs", "session", "workspace", "result"].includes(page);
  }

  return false;
}

function App() {
  const [currentPage, setCurrentPage] = useState("home");
  const [authPage, setAuthPage] = useState("login");
  const [labSession, setLabSession] = useState(null);
  const [authUser, setAuthUser] = useState(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);

  useEffect(() => {
    async function restoreAuthSession() {
      try {
        const authState = await getCurrentUser();

        if (authState?.user) {
          setAuthUser(authState.user);
          setCurrentPage(getDefaultPageForRole(authState.user.role));
        }
      } catch (error) {
        console.error("Auth session could not be restored.", error);
        logoutUser();
      } finally {
        setIsAuthLoading(false);
      }
    }

    restoreAuthSession();
  }, []);

  useEffect(() => {
    async function loadInitialLabData() {
      if (!authUser || authUser.role !== "student") {
        return;
      }

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

        if (isInactiveLabStatus(savedLabSession.status)) {
          clearTerminalTranscriptsForSession(savedSessionId);
          localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
          setLabSession(savedLabSession);
          return;
        }

        setLabSession(savedLabSession);
        setCurrentPage("workspace");
      } catch (error) {
        console.error("Initial lab session could not be loaded.", error);
        localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
      }
    }

    loadInitialLabData();
  }, [authUser]);

  function handleLoginSuccess(authState) {
    const user = authState?.user;

    if (!user) {
      return;
    }

    setAuthUser(user);
    setAuthPage("login");
    setCurrentPage(getDefaultPageForRole(user.role));
  }

  function handleLogout() {
    logoutUser();
    localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
    setAuthUser(null);
    setLabSession(null);
    setAuthPage("login");
    setCurrentPage("home");
  }

  function handleNavigate(page) {
    if (!authUser) {
      return;
    }

    if (!isPageAllowedForRole(page, authUser.role)) {
      setCurrentPage(getDefaultPageForRole(authUser.role));
      return;
    }

    setCurrentPage(page);
    scrollToPageTop();
  }

  function handleLabCreated(newLabSession) {
    setLabSession(newLabSession);

    if (newLabSession?.session_id && !isInactiveLabStatus(newLabSession.status)) {
      localStorage.setItem(
        ACTIVE_SESSION_STORAGE_KEY,
        newLabSession.session_id
      );
    } else {
      if (newLabSession?.session_id) {
        clearTerminalTranscriptsForSession(newLabSession.session_id);
      }

      localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
    }

    setCurrentPage("workspace");
    scrollToPageTop();
  }

  function handleLabUpdated(updatedLabSession) {
    setLabSession(updatedLabSession);

    if (updatedLabSession?.session_id && !isInactiveLabStatus(updatedLabSession.status)) {
      localStorage.setItem(
        ACTIVE_SESSION_STORAGE_KEY,
        updatedLabSession.session_id
      );
    } else {
      if (updatedLabSession?.session_id) {
        clearTerminalTranscriptsForSession(updatedLabSession.session_id);
      }

      localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
    }
  }

  async function handleLabSelectedFromHistory(labSummary, targetPage = "session") {
    const sessionId = labSummary?.session_id;

    if (!sessionId) {
      throw new Error("Selected lab does not include a session ID.");
    }

    const fullLabSession = await getLab(sessionId);
    setLabSession(fullLabSession);

    if (!isInactiveLabStatus(fullLabSession.status)) {
      localStorage.setItem(ACTIVE_SESSION_STORAGE_KEY, sessionId);
    } else {
      clearTerminalTranscriptsForSession(sessionId);
      localStorage.removeItem(ACTIVE_SESSION_STORAGE_KEY);
    }

    setCurrentPage(targetPage);
    scrollToPageTop();

    return fullLabSession;
  }

  if (isAuthLoading) {
    return (
      <main className="page">
        <section className="card auth-loading-state">
          <h2>Loading AutoNetLab</h2>
          <p className="muted">Checking the current authentication session...</p>
        </section>
      </main>
    );
  }

  if (!authUser) {
    if (authPage === "register") {
      return (
        <RegisterPage
          onNavigateLogin={() => setAuthPage("login")}
        />
      );
    }

    return (
      <LoginPage
        onLoginSuccess={handleLoginSuccess}
        onNavigateRegister={() => setAuthPage("register")}
      />
    );
  }

  const effectivePage = isPageAllowedForRole(currentPage, authUser.role)
    ? currentPage
    : getDefaultPageForRole(authUser.role);

  return (
    <Layout
      currentPage={effectivePage}
      onNavigate={handleNavigate}
      authUser={authUser}
      onLogout={handleLogout}
    >
      {authUser.role === "student" && effectivePage === "home" && (
        <Home labSession={labSession} onNavigate={handleNavigate} />
      )}

      {authUser.role === "student" && effectivePage === "create" && (
        <CreateLab
          authUser={authUser}
          onLabCreated={handleLabCreated}
          onNavigate={handleNavigate}
        />
      )}

      {authUser.role === "student" && effectivePage === "myLabs" && (
        <MyLabsPage
          authUser={authUser}
          onLabSelected={handleLabSelectedFromHistory}
          onNavigate={handleNavigate}
        />
      )}

      {authUser.role === "student" && effectivePage === "session" && (
        <SessionDetail
          labSession={labSession}
          onLabUpdated={handleLabUpdated}
          onNavigate={handleNavigate}
        />
      )}

      {authUser.role === "student" && effectivePage === "workspace" && (
        <LabWorkspacePage
          labSession={labSession}
          onLabUpdated={handleLabUpdated}
          onNavigate={handleNavigate}
        />
      )}

      {authUser.role === "student" && effectivePage === "result" && (
        <ValidationResult
          labSession={labSession}
          onLabUpdated={handleLabUpdated}
          onNavigate={handleNavigate}
        />
      )}

      {authUser.role === "instructor" && effectivePage === "instructor" && (
        <InstructorDashboardPage />
      )}
    </Layout>
  );
}

export default App;
