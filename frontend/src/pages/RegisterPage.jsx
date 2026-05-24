import { useEffect, useMemo, useState } from "react";
import MessageBox from "../components/MessageBox";
import {
  getErrorDetails,
  getErrorMessage,
  registerUser
} from "../services/apiService";

const FIELD_HELPERS = {
  username: "Choose a unique username for signing in.",
  password: "Password must be at least 6 characters.",
  display_name: "This name will be shown in the AutoNetLab interface.",
  email: "Optional. Use a valid email format if you provide one.",
  student_id: "This ID links lab sessions to your student account."
};

function createDefaultStudentId(username) {
  return String(username || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

function isValidEmail(value) {
  if (!value) {
    return true;
  }

  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function validateRegisterForm(form, suggestedStudentId) {
  const errors = {};
  const username = form.username.trim();
  const password = form.password;
  const email = form.email.trim();
  const studentId = form.student_id.trim() || suggestedStudentId || username;

  if (!username) {
    errors.username = "Username is required.";
  } else if (username.length < 3) {
    errors.username = "Username must be at least 3 characters.";
  }

  if (!password) {
    errors.password = "Password is required.";
  } else if (password.length < 6) {
    errors.password = "Password must be at least 6 characters.";
  }

  if (!isValidEmail(email)) {
    errors.email = "Enter a valid email address or leave this field empty.";
  }

  if (!studentId) {
    errors.student_id = "Student ID is required.";
  } else if (studentId.length < 3) {
    errors.student_id = "Student ID must be at least 3 characters.";
  }

  return errors;
}

function getRegisterErrorMessage(error) {
  const errorCode = error?.errorCode || error?.data?.error_code || "";
  const fallbackMessage = getErrorMessage(
    error,
    "Registration failed. Please review the form and try again."
  );

  if (errorCode === "USERNAME_ALREADY_EXISTS") {
    return "This username is already taken. Please choose another username.";
  }

  if (errorCode === "VALIDATION_ERROR") {
    return "Some registration fields are invalid. Please review the highlighted fields.";
  }

  return fallbackMessage;
}

function RegisterPage({ onNavigateLogin }) {
  const [form, setForm] = useState({
    username: "",
    password: "",
    display_name: "",
    email: "",
    student_id: ""
  });
  const [focusedField, setFocusedField] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [errorDetails, setErrorDetails] = useState("");

  const suggestedStudentId = useMemo(
    () => createDefaultStudentId(form.username),
    [form.username]
  );

  useEffect(() => {
    if (!successMessage) {
      return undefined;
    }

    const redirectTimer = window.setTimeout(() => {
      onNavigateLogin();
    }, 3000);

    return () => window.clearTimeout(redirectTimer);
  }, [successMessage, onNavigateLogin]);

  function updateField(field, value) {
    setForm((currentForm) => ({
      ...currentForm,
      [field]: value
    }));

    setFieldErrors((currentErrors) => ({
      ...currentErrors,
      [field]: ""
    }));
  }

  function getFieldHelp(field) {
    if (fieldErrors[field]) {
      return <p className="field-error">{fieldErrors[field]}</p>;
    }

    if (focusedField === field && FIELD_HELPERS[field]) {
      return <p className="form-helper">{FIELD_HELPERS[field]}</p>;
    }

    return null;
  }

  async function handleSubmit(event) {
    event.preventDefault();

    const validationErrors = validateRegisterForm(form, suggestedStudentId);

    setFieldErrors(validationErrors);
    setSuccessMessage("");
    setErrorMessage("");
    setErrorDetails("");

    if (Object.keys(validationErrors).length > 0) {
      setErrorMessage("Please fix the highlighted fields before creating the account.");
      return;
    }

    setIsSubmitting(true);

    const username = form.username.trim();
    const displayName = form.display_name.trim() || username;
    const studentId = form.student_id.trim() || suggestedStudentId || username;

    try {
      const result = await registerUser({
        username,
        password: form.password,
        display_name: displayName,
        email: form.email.trim() || undefined,
        student_id: studentId
      });

      setSuccessMessage(
        result?.message ||
          "Registration successful. Redirecting you to the sign in page..."
      );

      setForm({
        username: "",
        password: "",
        display_name: "",
        email: "",
        student_id: ""
      });
      setFieldErrors({});
    } catch (error) {
      const errorCode = error?.errorCode || error?.data?.error_code || "";

      if (errorCode === "USERNAME_ALREADY_EXISTS") {
        setFieldErrors((currentErrors) => ({
          ...currentErrors,
          username: "This username is already taken. Please choose another username."
        }));
      }

      setErrorMessage(getRegisterErrorMessage(error));
      setErrorDetails(getErrorDetails(error));
      console.error("Registration failed.", error);
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-brand">
          <span className="auth-badge">Student Registration</span>
          <h1>Create AutoNetLab Account</h1>
          <p>
            Create a student account to start lab sessions, save your lab history,
            and receive validation-based learning recommendations.
          </p>
        </div>

        {successMessage && (
          <MessageBox
            type="success"
            title="Registration successful"
            message={`${successMessage} You will be redirected in a few seconds.`}
          />
        )}

        {errorMessage && (
          <>
            <MessageBox
              type="error"
              title="Registration failed"
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
            <label htmlFor="registerUsername">Username</label>
            <input
              id="registerUsername"
              value={form.username}
              onFocus={() => setFocusedField("username")}
              onBlur={() => setFocusedField("")}
              onChange={(event) => updateField("username", event.target.value)}
              autoComplete="username"
              placeholder="alice"
              aria-invalid={Boolean(fieldErrors.username)}
            />
            {getFieldHelp("username")}
          </div>

          <div className={`form-group ${fieldErrors.password ? "has-error" : ""}`}>
            <label htmlFor="registerPassword">Password</label>
            <div className="password-input-wrapper">
              <input
                id="registerPassword"
                type={showPassword ? "text" : "password"}
                value={form.password}
                onFocus={() => setFocusedField("password")}
                onBlur={() => setFocusedField("")}
                onChange={(event) => updateField("password", event.target.value)}
                autoComplete="new-password"
                placeholder="At least 6 characters"
                aria-invalid={Boolean(fieldErrors.password)}
              />
              <button
                className="password-toggle-button"
                type="button"
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => setShowPassword((currentValue) => !currentValue)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? "Hide" : "Show"}
              </button>
            </div>
            {getFieldHelp("password")}
          </div>

          <div className={`form-group ${fieldErrors.display_name ? "has-error" : ""}`}>
            <label htmlFor="registerDisplayName">Display name</label>
            <input
              id="registerDisplayName"
              value={form.display_name}
              onFocus={() => setFocusedField("display_name")}
              onBlur={() => setFocusedField("")}
              onChange={(event) => updateField("display_name", event.target.value)}
              placeholder="Alice Student"
            />
            {getFieldHelp("display_name")}
          </div>

          <div className={`form-group ${fieldErrors.email ? "has-error" : ""}`}>
            <label htmlFor="registerEmail">Email</label>
            <input
              id="registerEmail"
              type="email"
              value={form.email}
              onFocus={() => setFocusedField("email")}
              onBlur={() => setFocusedField("")}
              onChange={(event) => updateField("email", event.target.value)}
              placeholder="alice@example.com"
              aria-invalid={Boolean(fieldErrors.email)}
            />
            {getFieldHelp("email")}
          </div>

          <div className={`form-group ${fieldErrors.student_id ? "has-error" : ""}`}>
            <label htmlFor="registerStudentId">Student ID</label>
            <input
              id="registerStudentId"
              value={form.student_id || suggestedStudentId}
              onFocus={() => setFocusedField("student_id")}
              onBlur={() => setFocusedField("")}
              onChange={(event) => updateField("student_id", event.target.value)}
              placeholder="alice"
              aria-invalid={Boolean(fieldErrors.student_id)}
            />
            {getFieldHelp("student_id")}
          </div>

          <button
            className="primary-button login-button"
            type="submit"
            disabled={isSubmitting}
          >
            {isSubmitting ? "Creating account..." : "Create account"}
          </button>
        </form>

        <div className="auth-switch-panel">
          <span className="muted">Already have an account?</span>
          <button
            className="link-button"
            type="button"
            onClick={onNavigateLogin}
          >
            Back to sign in
          </button>
        </div>
      </section>
    </main>
  );
}

export default RegisterPage;
