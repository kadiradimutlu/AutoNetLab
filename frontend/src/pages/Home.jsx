import StatCard from "../components/StatCard";
import MessageBox from "../components/MessageBox";
import { useLanguage } from "../hooks/useLanguage";
import {
  formatDifficulty,
  formatStatus
} from "../utils/formatters";

function Home({ labSession, onNavigate }) {
  const { t } = useLanguage();

  return (
    <>
      <section className="hero">
        <h2>{t("dashboardTitle")}</h2>
        <p>{t("dashboardDescription")}</p>

        <div className="actions">
          <button className="primary-button" onClick={() => onNavigate("create")}>
            {t("createNewLab")}
          </button>

          <button className="secondary-button" onClick={() => onNavigate("session")}>
            {t("viewCurrentLab")}
          </button>
        </div>
      </section>

      {!labSession && (
        <MessageBox
          type="info"
          title={t("loadingLabDataTitle")}
          message={t("loadingLabDataMessage")}
        />
      )}

      <section className="grid">
        <StatCard
          title={t("currentLab")}
          value={labSession?.session_id || "-"}
          helper={t("activeLabSessionIdentifier")}
        />

        <StatCard
          title={t("difficulty")}
          value={formatDifficulty(labSession?.difficulty, t)}
          helper={t("selectedLabDifficultyLevel")}
        />

        <StatCard
          title={t("status")}
          value={formatStatus(labSession?.status, t)}
          helper={t("currentLabSessionStatus")}
        />

        <StatCard
          title={t("injectedErrors")}
          value={labSession?.injected_errors?.length ?? 0}
          helper={t("numberOfGeneratedErrors")}
        />
      </section>
    </>
  );
}

export default Home;