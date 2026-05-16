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

          <button className="secondary-button" onClick={() => onNavigate("myLabs")}>
            My Labs
          </button>

          <button className="secondary-button" onClick={() => onNavigate("session")}>
            {t("viewCurrentLab")}
          </button>
        </div>
      </section>

      {!labSession && (
        <MessageBox
          type="info"
          title="No active lab session"
          message="Create a new lab session to start testing with the backend API."
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
          title="Student-safe View"
          value="Enabled"
          helper="Injected error details are hidden from student pages."
        />
      </section>
    </>
  );
}

export default Home;
