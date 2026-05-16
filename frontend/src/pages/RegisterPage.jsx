import { useMemo, useState } from "react";
import MessageBox from "../components/MessageBox";
import {
  getErrorDetails,
  getErrorMessage,
  registerUser
} from "../services/apiService";

function createDefaultStudentId(username) {
  return String(username || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

function RegisterPage({ onNavigateLogin }) {
  const [form, setForm] = useState({
    username: "",
    password: "",
    display_name: "",
    email: "",
    student_id: ""
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [errorDetails, setErrorDetails] = useState("");

  const suggestedStudentId = useMemo(
    () => createDefaultStudentId(form.username),
    [form.username]
  );

  function updateField(field, value) {
    setForm((currentForm) => ({
      ...currentForm,
      [field]: value
    }));
  }

  async function handleSubmit(event) {
    event.preventDefault();

    setIsSubmitting(true);
    setSuccessMessage("");
    setErrorMessage("");
    setErrorDetails("");

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
          "Registration successful. You can now sign in with your new student account."
      );

      setForm({
        username: "",
        password: "",
        display_name: "",
        email: "",
        student_id: ""
      });
    } catch (error) {
      setErrorMessage(getErrorMessage(error, "Registration failed."));
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
            Register a new student account. Registered users are created with the
            student role and can access their own lab history.
          </p>
        </div>

        {successMessage && (
          <MessageBox
            type="success"
            title="Registration successful"
            message={successMessage}
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
              <div className="technical-detail-box">
                <strong>Technical detail</strong>
                <p>{errorDetails}</p>
              </div>
            )}
          </>
        )}

        <form className="login-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="registerUsername">Username</label>
            <input
              id="registerUsername"
              value={form.username}
              onChange={(event) => updateField("username", event.target.value)}
              autoComplete="username"
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="registerPassword">Password</label>
            <input
              id="registerPassword"
              type="password"
              value={form.password}
              onChange={(event) => updateField("password", event.target.value)}
              autoComplete="new-password"
              required
              minLength={4}
            />
          </div>

          <div className="form-group">
            <label htmlFor="registerDisplayName">Display name</label>
            <input
              id="registerDisplayName"
              value={form.display_name}
              onChange={(event) => updateField("display_name", event.target.value)}
              placeholder="Alice Student"
            />
          </div>

          <div className="form-group">
            <label htmlFor="registerEmail">Email</label>
            <input
              id="registerEmail"
              type="email"
              value={form.email}
              onChange={(event) => updateField("email", event.target.value)}
              placeholder="alice@example.com"
            />
          </div>

          <div className="form-group">
            <label htmlFor="registerStudentId">Student ID</label>
            <input
              id="registerStudentId"
              value={form.student_id || suggestedStudentId}
              onChange={(event) => updateField("student_id", event.target.value)}
              placeholder="alice"
            />
            <p className="form-helper">
              This value is used by the backend to associate lab sessions with the student.
            </p>
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
