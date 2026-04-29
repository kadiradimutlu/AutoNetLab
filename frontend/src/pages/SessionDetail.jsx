import TopologyCard from "../components/TopologyCard";
import { useLanguage } from "../hooks/useLanguage";
import {
  formatDifficulty,
  formatStatus,
  formatStudentName,
  getDifficultyClass
} from "../utils/formatters";

function SessionDetail({ labSession, onNavigate }) {
  const { t } = useLanguage();

  if (!labSession) {
    return (
      <section className="card">
        <h2>{t("labSessionDetail")}</h2>
        <p className="muted">{t("labSessionLoading")}</p>
      </section>
    );
  }

  const difficultyClass = getDifficultyClass(labSession.difficulty);

  return (
    <div className="two-column">
      <section className="card">
        <h2>{t("labSessionDetail")}</h2>

        <div className="info-row">
          <span>{t("sessionId")}</span>
          <strong>{labSession.session_id}</strong>
        </div>

        <div className="info-row">
          <span>{t("student")}</span>
          <strong>{formatStudentName(labSession.student_id)}</strong>
        </div>

        <div className="info-row">
          <span>{t("difficulty")}</span>
          <span className={`badge ${difficultyClass}`}>
            {formatDifficulty(labSession.difficulty, t)}
          </span>
        </div>

        <div className="info-row">
          <span>{t("status")}</span>
          <strong>{formatStatus(labSession.status, t)}</strong>
        </div>

        <div className="info-row">
          <span>{t("injectedErrors")}</span>
          <strong>{labSession.injected_errors.length}</strong>
        </div>

        <h4>{t("injectedErrors")}</h4>
        <div className="result-list">
          {labSession.injected_errors.map((error) => (
            <div className="list-item" key={`${error.code}-${error.device}`}>
              <strong>{error.code}</strong>
              <p>{error.description}</p>
              <p className="muted">
                {t("topic")}: {error.topic} | {t("device")}: {error.device} |{" "}
                {t("severity")}: {error.severity}
              </p>
            </div>
          ))}
        </div>

        <h4>{t("cliAccess")}</h4>
        <div className="result-list">
          {labSession.cli_access.map((cli) => (
            <div className="list-item" key={cli.device_id}>
              <strong>{cli.device_id}</strong>
              <p className="muted">{cli.command}</p>
            </div>
          ))}
        </div>

        <div className="actions">
          <button className="primary-button" onClick={() => onNavigate("result")}>
            {t("validateLab")}
          </button>
        </div>

        <p className="footer-note">{t("backendFormatNote")}</p>
      </section>

      <TopologyCard topology={labSession.topology} />
    </div>
  );
}

export default SessionDetail;