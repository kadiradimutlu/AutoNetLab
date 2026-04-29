import { useState } from "react";
import ValidationSummary from "../components/ValidationSummary";
import RecommendationCard from "../components/RecommendationCard";
import MessageBox from "../components/MessageBox";
import { validateLab } from "../services/apiService";
import { useLanguage } from "../hooks/useLanguage";
import {
  formatDifficulty,
  formatStatus
} from "../utils/formatters";

function ValidationResult({ labSession }) {
  const { t } = useLanguage();

  const [validationResult, setValidationResult] = useState(null);
  const [isValidating, setIsValidating] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");

  async function handleValidate() {
    if (!labSession) {
      setErrorMessage(t("noActiveLab"));
      return;
    }

    setIsValidating(true);
    setErrorMessage("");

    try {
      const result = await validateLab(labSession.session_id);
      setValidationResult(result);
    } catch (error) {
      setErrorMessage(t("validationFailed"));
      console.error(error);
    } finally {
      setIsValidating(false);
    }
  }

  return (
    <>
      <section className="hero">
        <h2>{t("validationResultTitle")}</h2>
        <p>{t("validationResultDescription")}</p>

        {labSession && (
          <div className="session-mini-summary">
            <div>
              <span className="muted">{t("sessionId")}</span>
              <strong>{labSession.session_id}</strong>
            </div>

            <div>
              <span className="muted">{t("difficulty")}</span>
              <strong>{formatDifficulty(labSession.difficulty, t)}</strong>
            </div>

            <div>
              <span className="muted">{t("status")}</span>
              <strong>{formatStatus(labSession.status, t)}</strong>
            </div>
          </div>
        )}

        {errorMessage && (
          <MessageBox
            type="error"
            title={t("somethingWentWrong")}
            message={errorMessage}
          />
        )}

        <div className="actions">
          <button
            className="primary-button"
            onClick={handleValidate}
            disabled={isValidating}
          >
            {isValidating ? t("validating") : t("runValidation")}
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