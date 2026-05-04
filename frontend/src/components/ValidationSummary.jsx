import MessageBox from "./MessageBox";
import { useLanguage } from "../hooks/useLanguage";
import {
  getCheckStatusClass,
  getCheckStatusLabel,
  getValidationStatusClass,
  getValidationStatusLabel
} from "../utils/formatters";

function ValidationSummary({ validationResult, isValidating }) {
  const { t } = useLanguage();

  if (isValidating) {
    return (
      <section className="card">
        <h3>{t("validationResultTitle")}</h3>
        <MessageBox
          type="info"
          title={t("validationRunningTitle")}
          message={t("validationRunningMessage")}
        />
      </section>
    );
  }

  if (!validationResult) {
    return (
      <section className="card">
        <h3>{t("validationResultTitle")}</h3>
        <MessageBox
          type="empty"
          title={t("noValidationTitle")}
          message={t("noValidationMessage")}
        />
      </section>
    );
  }

  const checks = validationResult.checks || [];
  const totalChecks = checks.length;
  const passedChecks = checks.filter((check) => check.passed).length;
  const failedChecks = totalChecks - passedChecks;
  const score = validationResult.score ?? 0;

  return (
    <section className="card">
      <h3>{t("validationSummary")}</h3>

      <div className="validation-status-panel">
        <div>
          <span className={`badge ${getValidationStatusClass(validationResult)}`}>
            {getValidationStatusLabel(validationResult)}
          </span>

          <p>
            {validationResult.passed
              ? t("allChecksPassed")
              : t("someChecksFailed")}
          </p>
        </div>

        <div className="score-area">
          <div className="score-box">{score}/100</div>
          <div className="score-progress">
            <div
              className="score-progress-fill"
              style={{ width: `${Math.min(Math.max(score, 0), 100)}%` }}
            />
          </div>
        </div>
      </div>

      <div className="validation-metrics">
        <div className="metric-card">
          <span>{t("totalChecks")}</span>
          <strong>{totalChecks}</strong>
        </div>

        <div className="metric-card">
          <span>{t("passedChecks")}</span>
          <strong>{passedChecks}</strong>
        </div>

        <div className="metric-card">
          <span>{t("failedChecks")}</span>
          <strong>{failedChecks}</strong>
        </div>
      </div>

      <h4>{t("checkDetails")}</h4>

      <div className="result-list">
        {checks.map((check) => (
          <div className="list-item" key={check.check_id}>
            <div className="result-title-row">
              <strong>{check.topic}</strong>
              <span className={`badge ${getCheckStatusClass(check.passed)}`}>
                {getCheckStatusLabel(check.passed)}
              </span>
            </div>

            <p className="check-message">{check.message}</p>
            <p className="muted">
              {t("checkId")}: {check.check_id}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default ValidationSummary;