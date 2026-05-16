import { useState } from "react";
import MessageBox from "../components/MessageBox";
import {
  getErrorDetails,
  getErrorMessage,
  loginUser
} from "../services/apiService";

const DEMO_ACCOUNTS = [
  {
    role: "Student",
    username: "student",
    password: "student123",
    title: "Demo Student Login",
    description: "Use the student workspace, create labs, open My Labs, and troubleshoot with Web CLI."
  },
  {
    role: "Instructor",
    username: "instructor",
    password: "instructor123",
    title: "Demo Instructor Login",
    description: "Open the instructor dashboard and review analytics, readiness, and student progress."
  }
];

function LoginPage({ onLoginSuccess, onNavigateRegister }) {
  const [username, setUsername] = useState("student");
  const [password, setPassword] = useState("student123");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [errorDetails, setErrorDetails] = useState("");

  async function submitLogin(credentials) {
    setIsSubmitting(true);
    setErrorMessage("");
    setErrorDetails("");

    try {
      const authState = await loginUser(credentials);
      onLoginSuccess(authState);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Login failed."));
      setErrorDetails(getErrorDetails(error));
      console.error("Login failed.", error);
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleSubmit(event) {
    event.preventDefault();
    submitLogin({
      username,
      password
    });
  }

  function handleDemoLogin(account) {
    setUsername(account.username);
    setPassword(account.password);
    submitLogin({
      username: account.username,
      password: account.password
    });
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-brand">
          <span className="auth-badge">Sprint 22 Auth</span>
          <h1>AutoNetLab</h1>
          <p>
            Sign in to access role-aware lab workflows, Web CLI troubleshooting,
            My Labs history, and instructor analytics.
          </p>
        </div>

        {errorMessage && (
          <>
            <MessageBox
              type="error"
              title="Login failed"
              message={errorMessage}
            />

            {errorDetails && (
              <div className="technical-detail-box">
                <strong>Technical detail</strong>
                <p>{errorDetails}</p>
              </div>
            )}
          </>
        )}

        <form className="login-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="loginUsername">Username</label>
            <input
              id="loginUsername"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="loginPassword">Password</label>
            <input
              id="loginPassword"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
          </div>

          <button
            className="primary-button login-button"
            type="submit"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div className="auth-switch-panel">
          <span className="muted">New student account?</span>
          <button
            className="link-button"
            type="button"
            onClick={onNavigateRegister}
          >
            Create an account
          </button>
        </div>

        <div className="demo-account-grid">
          {DEMO_ACCOUNTS.map((account) => (
            <button
              className="demo-account-card"
              key={account.username}
              type="button"
              onClick={() => handleDemoLogin(account)}
              disabled={isSubmitting}
            >
              <span className="auth-role-pill">{account.role}</span>
              <strong>{account.title}</strong>
              <small>
                {account.username} / {account.password}
              </small>
              <p>{account.description}</p>
            </button>
          ))}
        </div>
      </section>
    </main>
  );
}

export default LoginPage;
