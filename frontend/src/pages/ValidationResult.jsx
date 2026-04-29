import { useEffect, useState } from "react";
import ValidationSummary from "../components/ValidationSummary";
import RecommendationCard from "../components/RecommendationCard";
import { getRecommendation, validateSession } from "../services/apiService";

function ValidationResult({ session }) {
  const [validationResult, setValidationResult] = useState(null);
  const [recommendation, setRecommendation] = useState(null);
  const [isValidating, setIsValidating] = useState(false);

  useEffect(() => {
    async function loadRecommendation() {
      if (!session) return;

      const recommendationData = await getRecommendation(session.sessionId);
      setRecommendation(recommendationData);
    }

    loadRecommendation();
  }, [session]);

  async function handleValidate() {
    if (!session) return;

    setIsValidating(true);

    try {
      const result = await validateSession(session.sessionId);
      setValidationResult(result);
    } catch (error) {
      alert("Validation failed.");
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
          Run validation to check whether the user configuration satisfies the
          expected network state. The result is currently generated from mock data.
        </p>

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
        <ValidationSummary validationResult={validationResult} />
        <RecommendationCard recommendation={recommendation} />
      </div>
    </>
  );
}

export default ValidationResult;