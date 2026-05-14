import { useState } from "react";
import MessageBox from "../components/MessageBox";
import {
  getErrorDetails,
  getErrorMessage,
  loginUser
} from "../services/apiService";

const DEMO_ACCOUNTS = [
  {
    role: "student",
    title: "Student Demo",
    username: "student",
    password: "student123",
    description: "Access student lab creation, CLI access, validation, and recommendations."
  },
  {
    role: "instructor",
    title: "Instructor Demo",
    username: "instructor",
    password: "instructor123",
    description: "Access instructor analytics and role-protected dashboard pages."
  }
];

function LoginPage({ onLoginSuccess }) {
  const [username, setUsername] = useState("student");
  const [password, setPassword] = useState("student123");
  const [isLoggingIn, setIsLoggingIn] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [errorDetails, setErrorDetails] = useState("");

  function fillDemoAccount(account) {
    setUsername(account.username);
    setPassword(account.password);
    setErrorMessage("");
    setErrorDetails("");
  }

  async function handleSubmit(event) {
    event.preventDefault();

    setIsLoggingIn(true);
    setErrorMessage("");
    setErrorDetails("");

    try {
      const authState = await loginUser({
        username,
        password
      });

      onLoginSuccess(authState);
    } catch (error) {
      setErrorMessage(
        getErrorMessage(
          error,
          "Login failed. Please check the username and password."
        )
      );
      setErrorDetails(getErrorDetails(error));
      console.error("Login failed.", error);
    } finally {
      setIsLoggingIn(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-brand">
          <span className="auth-badge">AutoNetLab</span>
          <h1>Sign in to AutoNetLab</h1>
          <p>
            Use a demo account to access the student lab flow or the instructor dashboard.
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
            <label htmlFor="username">Username</label>
            <input
              id="username"
              value={username}
              onChange={(event) => setUsername(event.target.value)}
              autoComplete="username"
              placeholder="student"
            />
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              placeholder="student123"
            />
          </div>

          <button className="primary-button login-button" disabled={isLoggingIn}>
            {isLoggingIn ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <div className="demo-account-grid">
          {DEMO_ACCOUNTS.map((account) => (
            <button
              className="demo-account-card"
              key={account.role}
              onClick={() => fillDemoAccount(account)}
              type="button"
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
