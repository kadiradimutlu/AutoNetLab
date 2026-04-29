import { useState } from "react";
import ValidationSummary from "../components/ValidationSummary";
import RecommendationCard from "../components/RecommendationCard";
import MessageBox from "../components/MessageBox";
import { validateLab } from "../services/apiService";
import {
  formatDifficulty,
  formatStatus
} from "../utils/formatters";

function ValidationResult({ labSession }) {
  const [validationResult, setValidationResult] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  async function handleValidate() {
    if (!labSession) {
      setErrorMessage("There is no active lab session to validate.");
      return;
    }

    setIsValidating(true);
    setErrorMessage("");

    try {
      const result = await validateLab(labSession.session_id);
      setValidationResult(result);
    } catch (error) {
      setErrorMessage("Validation failed. Please try again.");
      console.error(error);
    } finally {
      setIsValidating(false);
    }
  }

  return (
    <>
      <section className="hero">
        <h2>Validation Result / Doğrulama Sonucu</h2>
        <p>
          Run validation to check whether the current network configuration
          satisfies the expected topology state. The response format now follows
          the backend ValidationResult schema.
        </p>

        {labSession && (
          <div className="session-mini-summary">
            <div>
              <span className="muted">Session</span>
              <strong>{labSession.session_id}</strong>
            </div>

            <div>
              <span className="muted">Difficulty</span>
              <strong>{formatDifficulty(labSession.difficulty)}</strong>
            </div>

            <div>
              <span className="muted">Status</span>
              <strong>{formatStatus(labSession.status)}</strong>
            </div>
          </div>
        )}

        {errorMessage && (
          <MessageBox
            type="error"
            title="Something went wrong"
            message={errorMessage}
          />
        )}

        <div className="actions">
          <button
            className="primary-button"
            onClick={handleValidate}
            disabled={isValidating}
          >
            {isValidating ? "Validating..." : "Run Validation"}
          </button>
        </div>
      </section>

      <div className="two-column">
        <ValidationSummary
          validationResult={validationResult}
          isValidating={isValidating}
        />

        <RecommendationCard
          recommendations={validationResult?.recommendations || []}
        />
      </div>
    </>
  );
}

export default ValidationResult;