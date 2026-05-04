import { useLanguage } from "../hooks/useLanguage";

function RecommendationCard({ recommendations = [] }) {
  const { t } = useLanguage();

  const safeRecommendations = Array.isArray(recommendations)
    ? recommendations
    : [recommendations];

  if (!safeRecommendations.length) {
    return (
      <section className="card">
        <h3>{t("recommendation")}</h3>
        <p className="muted">{t("recommendationEmpty")}</p>
      </section>
    );
  }

  return (
    <section className="card">
      <h3>{t("recommendation")}</h3>

      <div className="recommendation-list">
        {safeRecommendations.map((message, index) => (
          <div className="list-item" key={`${String(message)}-${index}`}>
            <strong>
              {t("recommendationNumber")} {index + 1}
            </strong>
            <p>{String(message)}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default RecommendationCard;