import MessageBox from "./MessageBox";

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

function getDisplayValue(value, fallback = "-") {
  if (value === undefined || value === null || value === "") {
    return fallback;
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

function toReadableLabel(value) {
  return getDisplayValue(value)
    .replace(/[_-]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function normalizeStatus(check) {
  const rawStatus = String(check.status || "").toLowerCase();

  if (rawStatus.includes("pass") || rawStatus === "success") {
    return "pass";
  }

  if (rawStatus.includes("fail") || rawStatus === "error") {
    return "fail";
  }

  if (check.passed === true) {
    return "pass";
  }

  if (check.passed === false) {
    return "fail";
  }

  return "unknown";
}

function getStatusLabel(status) {
  if (status === "pass") {
    return "PASS";
  }

  if (status === "fail") {
    return "FAIL";
  }

  return "UNKNOWN";
}

function getStatusClass(status) {
  if (status === "pass") {
    return "pass";
  }

  if (status === "fail") {
    return "fail";
  }

  return "neutral";
}

function getCheckTitle(check, index) {
  return (
    check.description ||
    check.message ||
    toReadableLabel(check.check_id || check.id || `Validation Check ${index + 1}`)
  );
}

function getCheckPoints(check) {
  const points = check.points ?? check.score ?? 0;
  const maxPoints = check.max_points ?? check.maxPoints ?? 0;

  if (maxPoints) {
    return `${points}/${maxPoints}`;
  }

  return getDisplayValue(points, "0");
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

  return matchedRule?.label || toReadableLabel(check.topic || check.category || "General Validation");
}

function getStudentSafeHint(check, status) {
  if (status === "pass") {
    return "This check currently matches the expected state.";
  }

  return (
    check.hint ||
    check.message ||
    "Compare this area with the scenario design guide, update the live configuration, and run validation again."
  );
}

function groupChecksByFocusArea(checks) {
  return checks.reduce((groups, check) => {
    const focusArea = getFocusArea(check);

    if (!groups[focusArea]) {
      groups[focusArea] = [];
    }

    groups[focusArea].push(check);
    return groups;
  }, {});
}

function sortChecksForLearning(checks) {
  return [...checks].sort((left, right) => {
    const leftStatus = normalizeStatus(left);
    const rightStatus = normalizeStatus(right);

    if (leftStatus === rightStatus) {
      return String(left.check_id || "").localeCompare(String(right.check_id || ""));
    }

    if (leftStatus === "fail") {
      return -1;
    }

    if (rightStatus === "fail") {
      return 1;
    }

    if (leftStatus === "unknown") {
      return -1;
    }

    if (rightStatus === "unknown") {
      return 1;
    }

    return 0;
  });
}

function ValidationCheckCard({ check, index, compact = false }) {
  const status = normalizeStatus(check);
  const focusArea = getFocusArea(check);

  return (
    <div
      className={`list-item check-card validation-check-card-polished ${
        status === "pass" ? "passed-check-card" : "failed-check-card"
      } ${compact ? "compact" : ""}`}
      key={check.check_id || `${focusArea}-${index}`}
    >
      <div className="result-title-row validation-check-title-row">
        <div>
          <strong>{getCheckTitle(check, index)}</strong>
          <p className="muted">
            Check ID: {getDisplayValue(check.check_id || check.id, `check-${index + 1}`)}
          </p>
        </div>

        <span className={`badge ${getStatusClass(status)}`}>
          {getStatusLabel(status)}
        </span>
      </div>

      <div className="check-detail-grid advanced-check-grid validation-check-grid-polished">
        <div>
          <span>Focus Area</span>
          <strong>{focusArea}</strong>
        </div>

        <div>
          <span>Points</span>
          <strong>{getCheckPoints(check)}</strong>
        </div>

        <div>
          <span>Status</span>
          <strong>{getStatusLabel(status)}</strong>
        </div>

        <div>
          <span>Learning Hint</span>
          <strong>{getStudentSafeHint(check, status)}</strong>
        </div>
      </div>

      {check.message && status !== "pass" && (
        <p className="check-message">{check.message}</p>
      )}
    </div>
  );
}

function ValidationCheckList({ checks = [] }) {
  if (!checks.length) {
    return (
      <MessageBox
        type="empty"
        title="No check details"
        message="No checks list was found in the validation response."
      />
    );
  }

  const groupedChecks = groupChecksByFocusArea(sortChecksForLearning(checks));

  return (
    <div className="validation-topic-list validation-topic-list-polished">
      {Object.entries(groupedChecks).map(([focusArea, focusChecks], topicIndex) => {
        const failedOrUnknownChecks = focusChecks.filter((check) => normalizeStatus(check) !== "pass");
        const passedChecks = focusChecks.filter((check) => normalizeStatus(check) === "pass");
        const failedCount = failedOrUnknownChecks.length;

        return (
          <section
            className={`validation-topic-group validation-topic-group-polished ${
              failedCount > 0 ? "has-failures" : "all-passed"
            }`}
            key={focusArea}
          >
            <div className="validation-topic-header">
              <div>
                <span className="muted">Focus Area</span>
                <h4>{focusArea}</h4>
              </div>

              <div className="validation-topic-badge-row">
                {failedCount > 0 && (
                  <span className="badge fail">
                    {failedCount} failed
                  </span>
                )}

                <span className="badge neutral">
                  {focusChecks.length} {focusChecks.length === 1 ? "check" : "checks"}
                </span>
              </div>
            </div>

            {failedOrUnknownChecks.length > 0 && (
              <div className="result-list validation-priority-checks">
                {failedOrUnknownChecks.map((check, index) => (
                  <ValidationCheckCard
                    check={check}
                    index={index}
                    key={check.check_id || `${focusArea}-failed-${index}`}
                  />
                ))}
              </div>
            )}

            {passedChecks.length > 0 && (
              <details
                className="validation-passed-checks-panel"
                open={failedOrUnknownChecks.length === 0 && topicIndex === 0}
              >
                <summary>
                  {failedOrUnknownChecks.length > 0 ? "Show" : "Review"} {passedChecks.length} passed {passedChecks.length === 1 ? "check" : "checks"}
                </summary>

                <div className="result-list validation-passed-checks-list">
                  {passedChecks.map((check, index) => (
                    <ValidationCheckCard
                      check={check}
                      index={index}
                      compact
                      key={check.check_id || `${focusArea}-passed-${index}`}
                    />
                  ))}
                </div>
              </details>
            )}
          </section>
        );
      })}
    </div>
  );
}

export default ValidationCheckList;
