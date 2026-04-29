import { useEffect, useState } from "react";
import ValidationSummary from "../components/ValidationSummary";
import RecommendationCard from "../components/RecommendationCard";
import MessageBox from "../components/MessageBox";
import { getRecommendation, validateSession } from "../services/apiService";

function ValidationResult({ session }) {
  const [validationResult, setValidationResult] = useState(null);
  const [recommendation, setRecommendation] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  useEffect(() => {
    async function loadRecommendation() {
      if (!session) return;

      try {
        const recommendationData = await getRecommendation(session.sessionId);
        setRecommendation(recommendationData);
      } catch (error) {
        setErrorMessage("Recommendation data could not be loaded.");
        console.error(error);
      }
    }

    loadRecommendation();
  }, [session]);

  async function handleValidate() {
    if (!session) {
      setErrorMessage("There is no active session to validate.");
      return;
    }

    setIsValidating(true);
    setErrorMessage("");

    try {
      const result = await validateSession(session.sessionId);
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
          satisfies the expected topology state. The result is currently generated
          from mock data.
        </p>

        {session && (
          <div className="session-mini-summary">
            <div>
              <span className="muted">Session</span>
              <strong>{session.sessionId}</strong>
            </div>

            <div>
              <span className="muted">Difficulty</span>
              <strong>{session.difficulty}</strong>
            </div>

            <div>
              <span className="muted">Status</span>
              <strong>{session.status}</strong>
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

        <RecommendationCard recommendation={recommendation} />
      </div>
    </>
  );
}

export default ValidationResult;