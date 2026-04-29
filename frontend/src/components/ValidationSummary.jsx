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

  const totalChecks = validationResult.checks.length;
  const passedChecks = validationResult.checks.filter((check) => check.passed).length;
  const failedChecks = totalChecks - passedChecks;

  return (
    <section className="card">
      <h3>{t("validationSummary")}</h3>

      <div className="validation-header">
        <span className={`badge ${getValidationStatusClass(validationResult)}`}>
          {getValidationStatusLabel(validationResult)}
        </span>

        <div className="score-box">{validationResult.score}/100</div>
      </div>

      <p>
        {validationResult.passed
          ? t("allChecksPassed")
          : t("someChecksFailed")}
      </p>

      <div className="info-row">
        <span>{t("totalChecks")}</span>
        <strong>{totalChecks}</strong>
      </div>

      <div className="info-row">
        <span>{t("passedChecks")}</span>
        <strong>{passedChecks}</strong>
      </div>

      <div className="info-row">
        <span>{t("failedChecks")}</span>
        <strong>{failedChecks}</strong>
      </div>

      <h4>{t("checkDetails")}</h4>

      <div className="result-list">
        {validationResult.checks.map((check) => (
          <div className="list-item" key={check.check_id}>
            <div className="result-title-row">
              <strong>{check.topic}</strong>
              <span className={`badge ${getCheckStatusClass(check.passed)}`}>
                {getCheckStatusLabel(check.passed)}
              </span>
            </div>

            <p>{check.message}</p>
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