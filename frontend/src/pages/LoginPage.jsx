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
    title: "Use Student Profile",
    description: "Fill in the student credentials for lab creation, My Labs, Web CLI, validation, and recommendations."
  },
  {
    role: "Instructor",
    username: "instructor",
    password: "instructor123",
    title: "Use Instructor Profile",
    description: "Fill in the instructor credentials for analytics, student progress, and system readiness views."
  }
];

function validateLoginForm({ username, password }) {
  const errors = {};

  if (!username.trim()) {
    errors.username = "Username is required.";
  }

  if (!password) {
    errors.password = "Password is required.";
  }

  return errors;
}

function LoginPage({ onLoginSuccess, onNavigateRegister }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [errorDetails, setErrorDetails] = useState("");

  async function submitLogin(credentials) {
    const validationErrors = validateLoginForm(credentials);

    setFieldErrors(validationErrors);
    setErrorMessage("");
    setErrorDetails("");

    if (Object.keys(validationErrors).length > 0) {
      return;
    }

    setIsSubmitting(true);

    try {
      const authState = await loginUser(credentials);
      onLoginSuccess(authState);
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Login failed. Please check your credentials and try again."));
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

  function handleDemoFill(account) {
    setUsername(account.username);
    setPassword(account.password);
    setFieldErrors({});
    setErrorMessage("");
    setErrorDetails("");
  }

  function updateUsername(value) {
    setUsername(value);
    setFieldErrors((currentErrors) => ({
      ...currentErrors,
      username: ""
    }));
  }

  function updatePassword(value) {
    setPassword(value);
    setFieldErrors((currentErrors) => ({
      ...currentErrors,
      password: ""
    }));
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-brand">
          <h1>AutoNetLab</h1>
          <p>
            Sign in to manage your network lab sessions, access the browser-based
            Web CLI, review validation results, and continue from your lab history.
          </p>
        </div>

        {errorMessage && (
          <>
            <MessageBox
              type="error"
              title="Sign in failed"
              message={errorMessage}
            />

            {errorDetails && (
              <details className="technical-detail-box auth-technical-details">
                <summary>Show diagnostics</summary>
                <p>{errorDetails}</p>
              </details>
            )}
          </>
        )}

        <form className="login-form" onSubmit={handleSubmit} noValidate>
          <div className={`form-group ${fieldErrors.username ? "has-error" : ""}`}>
            <label htmlFor="loginUsername">Username</label>
            <input
              id="loginUsername"
              value={username}
              onChange={(event) => updateUsername(event.target.value)}
              autoComplete="username"
              placeholder="Enter your username"
              aria-invalid={Boolean(fieldErrors.username)}
            />
            {fieldErrors.username && (
              <p className="field-error">{fieldErrors.username}</p>
            )}
          </div>

          <div className={`form-group ${fieldErrors.password ? "has-error" : ""}`}>
            <label htmlFor="loginPassword">Password</label>
            <div className="password-input-wrapper">
              <input
                id="loginPassword"
                type={showPassword ? "text" : "password"}
                value={password}
                onChange={(event) => updatePassword(event.target.value)}
                autoComplete="current-password"
                placeholder="Enter your password"
                aria-invalid={Boolean(fieldErrors.password)}
              />
              <button
                className="password-toggle-button"
                type="button"
                onClick={() => setShowPassword((currentValue) => !currentValue)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
            {fieldErrors.password && (
              <p className="field-error">{fieldErrors.password}</p>
            )}
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

        <div className="demo-account-section">
          <div className="demo-account-heading">
            <strong>Quick sign-in profiles</strong>
            <span>Choose a profile to fill the form, then press Sign in.</span>
          </div>

          <div className="demo-account-grid">
            {DEMO_ACCOUNTS.map((account) => (
              <button
                className="demo-account-card"
                key={account.username}
                type="button"
                onClick={() => handleDemoFill(account)}
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
        </div>
      </section>
    </main>
  );
}

export default LoginPage;
