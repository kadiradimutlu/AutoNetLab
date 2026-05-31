import MessageBox from "./MessageBox";
import ValidationCheckList from "./ValidationCheckList";
import { useLanguage } from "../hooks/useLanguage";
import {
  getValidationStatusClass,
  getValidationStatusLabel
} from "../utils/formatters";

const CAMPUS_SCENARIO_ID = "campus-core-routing";

const FOCUS_AREA_RULES = [
  {
    label: "Default Gateway",
    keywords: ["default_gateway", "default gateway", "gateway", "client2_default_gateway"]
  },
  {
    label: "Connectivity",
    keywords: ["connectivity", "reachability", "ping", "client1_to_client2", "client2_to_client1"]
  },
  {
    label: "Static Routing",
    keywords: ["static_route", "static route", "route", "routing", "next-hop", "next hop"]
  },
  {
    label: "Interface State",
    keywords: ["interface", "admin-state", "oper-state", "link state", "link"]
  },
  {
    label: "IP Addressing",
    keywords: ["address", "ip address", "subnet", "prefix"]
  },
  {
    label: "Network Instance",
    keywords: ["network_instance", "network instance"]
  }
];

function isCheckPassed(check) {
  const status = String(check.status || "").toLowerCase();

  if (status.includes("pass") || status === "success") {
    return true;
  }

  if (status.includes("fail") || status === "error") {
    return false;
  }

  return Boolean(check.passed);
}

function getSafeNumber(value, fallback = 0) {
  const numericValue = Number(value);

  if (Number.isNaN(numericValue)) {
    return fallback;
  }

  return numericValue;
}

function clampScore(value, fallback = 0) {
  const numericValue = getSafeNumber(value, fallback);

  return Math.min(Math.max(Math.round(numericValue), 0), 100);
}

function getNetworkHealthScore(validationResult, checks) {
  if (validationResult.network_health_score !== undefined && validationResult.network_health_score !== null) {
    return clampScore(validationResult.network_health_score);
  }

  const earnedPoints = checks.reduce(
    (total, check) => total + getSafeNumber(check.points),
    0
  );
  const maxPoints = checks.reduce(
    (total, check) => total + getSafeNumber(check.max_points ?? check.maxPoints),
    0
  );

  if (!maxPoints) {
    return 0;
  }

  return clampScore((earnedPoints / maxPoints) * 100);
}

function getFaultResolutionScore(validationResult, checks) {
  if (validationResult.fault_resolution_score !== undefined && validationResult.fault_resolution_score !== null) {
    return clampScore(validationResult.fault_resolution_score);
  }

  if (validationResult.score !== undefined && validationResult.score !== null) {
    return clampScore(validationResult.score);
  }

  return getNetworkHealthScore(validationResult, checks);
}

function normalizeTopicList(value) {
  if (!value) {
    return [];
  }

  const rawItems = Array.isArray(value)
    ? value
    : typeof value === "object"
      ? Object.values(value)
      : [value];

  return rawItems
    .map((item) => {
      if (!item) {
        return "";
      }

      if (typeof item === "object") {
        return item.label || item.topic || item.name || item.id || "";
      }

      return String(item);
    })
    .filter(Boolean)
    .map((item) => String(item).replace(/_/g, " ").replace(/\s+/g, " ").trim())
    .filter(Boolean);
}

function getCheckSearchText(check) {
  return [
    check?.check_id,
    check?.id,
    check?.name,
    check?.label,
    check?.topic,
    check?.category,
    check?.description,
    check?.message,
    check?.hint
  ]
    .filter(Boolean)
    .map((item) => String(item).toLowerCase())
    .join(" ");
}

function getFocusArea(check) {
  const text = getCheckSearchText(check);

  const matchedRule = FOCUS_AREA_RULES.find((rule) =>
    rule.keywords.some((keyword) => text.includes(keyword))
  );

  return matchedRule?.label || "General Validation";
}

function getCheckIdentifier(check) {
  return [
    check?.check_id,
    check?.id,
    check?.name,
    check?.description,
    check?.message,
    check?.topic,
    check?.category
  ]
    .filter(Boolean)
    .map((item) => String(item).toLowerCase())
    .join(" ");
}

function isCampusValidation(validationResult, checks) {
  const identity = [
    validationResult?.scenario_id,
    validationResult?.topology_template,
    validationResult?.scenario,
    validationResult?.topology?.name,
    validationResult?.lab?.scenario_id
  ]
    .filter(Boolean)
    .map((item) => String(item).toLowerCase())
    .join(" ");

  const checkIdentity = checks.map((check) => getCheckIdentifier(check)).join(" ");

  return (
    identity.includes(CAMPUS_SCENARIO_ID) ||
    identity.includes("campus") ||
    checkIdentity.includes("campus_check") ||
    (checks.length >= 10 && checkIdentity.includes("client2") && checkIdentity.includes("srl"))
  );
}

function buildAreaSummary(failedChecks) {
  const areaMap = failedChecks.reduce((map, check) => {
    const area = getFocusArea(check);
    map.set(area, (map.get(area) || 0) + 1);
    return map;
  }, new Map());

  return Array.from(areaMap.entries()).map(([label, count]) => ({
    label,
    count
  }));
}

function getGuidanceMessage({ allChecksPassed, isCampus, failedAreas }) {
  if (allChecksPassed && isCampus) {
    return "Campus validation passed. Client gateways, SR Linux routing, interface state, and end-to-end connectivity are aligned.";
  }

  if (allChecksPassed) {
    return "All checks passed. Review the completed checks and recommendations for your final understanding.";
  }

  const hasDefaultGatewayIssue = failedAreas.some((area) => area.label === "Default Gateway");
  const hasConnectivityIssue = failedAreas.some((area) => area.label === "Connectivity");

  if (isCampus && (hasDefaultGatewayIssue || hasConnectivityIssue)) {
    return "Review the client default gateway and retest end-to-end connectivity.";
  }

  if (isCampus) {
    return "Review the failed campus areas, compare them with the design guide, and run validation again.";
  }

  return "Review failed topics and use the general hints before running validation again.";
}

function getNextSteps({ allChecksPassed, isCampus, failedAreas }) {
  if (allChecksPassed) {
    return [
      "Review the passed checks to confirm the expected network state.",
      "Finish the lab when you are ready to preserve the successful result."
    ];
  }

  const steps = [];

  if (failedAreas.some((area) => area.label === "Default Gateway")) {
    steps.push("Compare the client default gateway with the Addressing Table.");
  }

  if (failedAreas.some((area) => area.label === "Connectivity")) {
    steps.push("Retest client-to-client connectivity after fixing the failed area.");
  }

  if (failedAreas.some((area) => area.label === "Static Routing")) {
    steps.push("Inspect static routes and next-hop reachability across the SR Linux core.");
  }

  if (failedAreas.some((area) => area.label === "Interface State")) {
    steps.push("Confirm that the relevant SR Linux interfaces are administratively and operationally up.");
  }

  if (!steps.length) {
    steps.push("Start with the failed checks, then compare the live state with the scenario design guide.");
  }

  if (isCampus) {
    steps.push("Use Web CLI to update the live configuration, then run validation again.");
  }

  return steps.slice(0, 4);
}

function ValidationSummary({
  validationResult,
  isValidating
}) {
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

  const checks = Array.isArray(validationResult.checks)
    ? validationResult.checks
    : [];

  const computedPassedChecks = checks.filter((check) => isCheckPassed(check)).length;
  const totalChecks = validationResult.total_checks ?? checks.length;
  const passedChecks = validationResult.passed_checks ?? computedPassedChecks;
  const failedChecks = validationResult.failed_checks ?? Math.max(totalChecks - passedChecks, 0);
  const failedCheckItems = checks.filter((check) => !isCheckPassed(check));
  const allChecksPassed =
    validationResult.passed === true || (totalChecks > 0 && failedChecks === 0);
  const faultResolutionScore = getFaultResolutionScore(validationResult, checks);
  const networkHealthScore = getNetworkHealthScore(validationResult, checks);
  const affectedTopics = normalizeTopicList(validationResult.affected_topics || validationResult.affectedTopics);
  const failedTopics = normalizeTopicList(validationResult.failed_topics || validationResult.failedTopics);
  const resolvedTopics = normalizeTopicList(validationResult.resolved_topics || validationResult.resolvedTopics);
  const affectedTopicCount = validationResult.affected_topic_count ?? affectedTopics.length;
  const resolvedTopicCount = validationResult.resolved_topic_count ?? resolvedTopics.length;
  const failedTopicCount = validationResult.failed_topic_count ?? failedTopics.length;
  const isCampus = isCampusValidation(validationResult, checks);
  const failedAreas = buildAreaSummary(failedCheckItems);
  const guidanceMessage = getGuidanceMessage({
    allChecksPassed,
    isCampus,
    failedAreas
  });
  const nextSteps = getNextSteps({
    allChecksPassed,
    isCampus,
    failedAreas
  });

  return (
    <section
      className={`card validation-summary-card validation-summary-card-polished ${
        allChecksPassed ? "validation-pass" : "validation-fail"
      }`}
    >
      <div className="section-title-row validation-summary-title-row">
        <div>
          <h3>{t("validationSummary")}</h3>
          <p className="muted">
            Fault resolution, network health, affected topics, and network diagnostics for the current lab session.
          </p>
        </div>

        <span className={`badge ${getValidationStatusClass(validationResult)}`}>
          {getValidationStatusLabel(validationResult)}
        </span>
      </div>

      <div className="validation-result-hero">
        <div className="validation-result-copy">
          <span className={`validation-result-state ${allChecksPassed ? "pass" : "fail"}`}>
            {allChecksPassed ? "PASS" : "FAIL"}
          </span>
          <h4>
            {allChecksPassed
              ? "Validation completed successfully"
              : "Validation found issues to fix"}
          </h4>
          <p>{guidanceMessage}</p>
        </div>

        <div className="validation-score-panel">
          <span>Fault Resolution Score</span>
          <strong>{faultResolutionScore}/100</strong>
          <div className="score-progress">
            <div
              className="score-progress-fill"
              style={{ width: `${faultResolutionScore}%` }}
            />
          </div>
        </div>
      </div>

      <div className="validation-metrics validation-metrics-polished validation-contract-metrics">
        <div className="metric-card metric-pass">
          <span>Network Health Score</span>
          <strong>{networkHealthScore}/100</strong>
        </div>

        <div className="metric-card">
          <span>Affected Topics</span>
          <strong>{affectedTopicCount}</strong>
        </div>

        <div className="metric-card metric-pass">
          <span>Resolved Topics</span>
          <strong>{resolvedTopicCount}</strong>
        </div>

        <div className="metric-card metric-fail">
          <span>Topics Needing Review</span>
          <strong>{failedTopicCount}</strong>
        </div>
      </div>

      {(affectedTopics.length > 0 || failedTopics.length > 0 || resolvedTopics.length > 0) && (
        <div className="validation-focus-panel validation-topic-progress-panel">
          <div className="section-title-row compact">
            <div>
              <h4>Injected Fault Progress</h4>
              <p className="muted">
                These topics represent the fault-focused validation contract. Full network checks are listed separately below.
              </p>
            </div>
          </div>

          <div className="validation-focus-grid">
            {affectedTopics.map((topic) => (
              <article className="validation-focus-card" key={`affected-${topic}`}>
                <strong>{topic}</strong>
                <span>Affected topic</span>
              </article>
            ))}

            {resolvedTopics.map((topic) => (
              <article className="validation-focus-card" key={`resolved-${topic}`}>
                <strong>{topic}</strong>
                <span>Resolved</span>
              </article>
            ))}

            {failedTopics.map((topic) => (
              <article className="validation-focus-card" key={`failed-${topic}`}>
                <strong>{topic}</strong>
                <span>Needs review</span>
              </article>
            ))}
          </div>
        </div>
      )}

      <div className="validation-metrics validation-metrics-polished validation-network-check-metrics">
        <div className="metric-card">
          <span>Network Checks</span>
          <strong>{totalChecks}</strong>
        </div>

        <div className="metric-card metric-pass">
          <span>Passed Network Checks</span>
          <strong>{passedChecks}</strong>
        </div>

        <div className="metric-card metric-fail">
          <span>Failed Network Checks</span>
          <strong>{failedChecks}</strong>
        </div>
      </div>

      {!allChecksPassed && failedAreas.length > 0 && (
        <div className="validation-focus-panel">
          <div className="section-title-row compact">
            <div>
              <h4>Primary Failed Areas</h4>
              <p className="muted">Start here before changing the live configuration.</p>
            </div>

            {isCampus && <span className="badge neutral">Campus validation</span>}
          </div>

          <div className="validation-focus-grid">
            {failedAreas.map((area) => (
              <article className="validation-focus-card" key={area.label}>
                <strong>{area.label}</strong>
                <span>{area.count} failed {area.count === 1 ? "check" : "checks"}</span>
              </article>
            ))}
          </div>
        </div>
      )}

      <div className="validation-next-steps-panel">
        <div>
          <h4>{allChecksPassed ? "Completion Guidance" : "Recommended Next Steps"}</h4>
          <p className="muted">
            Guidance is based on validation status and avoids hidden runtime details.
          </p>
        </div>

        <ol className="validation-next-step-list">
          {nextSteps.map((step, index) => (
            <li key={step}>
              <span>{index + 1}</span>
              <p>{step}</p>
            </li>
          ))}
        </ol>
      </div>

      <div className="validation-check-section-header">
        <div>
          <h4>Validation Checks</h4>
          <p className="muted">
            Failed checks are shown first. Passed checks remain available without overwhelming the result view.
          </p>
        </div>
      </div>

      <ValidationCheckList checks={checks} />
    </section>
  );
}

export default ValidationSummary;
