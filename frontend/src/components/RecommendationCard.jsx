import { useLanguage } from "../hooks/useLanguage";

function RecommendationCard({ recommendations = [] }) {
  const { t } = useLanguage();

  if (!recommendations.length) {
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
        {recommendations.map((message, index) => (
          <div className="list-item" key={`${message}-${index}`}>
            <strong>
              {t("recommendationNumber")} {index + 1}
            </strong>
            <p>{message}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

export default RecommendationCard;