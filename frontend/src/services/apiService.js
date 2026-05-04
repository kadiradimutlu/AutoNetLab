import mockDifficulties from "../data/mock_difficulties.json";
import mockLabSession from "../data/mock_lab_session.json";
import mockValidationResult from "../data/mock_validation_result_backend.json";

const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API !== "false";
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

export function isMockApiEnabled() {
  return USE_MOCK_API;
}

const ERROR_COUNT_BY_DIFFICULTY = {
  easy: 2,
  medium: 3,
  hard: 5
};

const MOCK_ERROR_POOL = [
  {
    code: "IP_ADDRESS_MISMATCH",
    topic: "IP Addressing",
    device: "r1",
    description: "Incorrect IP address configured on r1 eth1.",
    severity: "low"
  },
  {
    code: "WRONG_SUBNET_MASK",
    topic: "IP Addressing",
    device: "r2",
    description: "Wrong subnet mask configured on r2 eth1.",
    severity: "low"
  },
  {
    code: "VLAN_MISMATCH",
    topic: "VLAN",
    device: "r1",
    description: "VLAN ID mismatch on r1 interface.",
    severity: "medium"
  },
  {
    code: "MISSING_ROUTE",
    topic: "Routing",
    device: "r2",
    description: "Static route is missing on r2.",
    severity: "medium"
  },
  {
    code: "ACL_DENY_ANY",
    topic: "ACL",
    device: "r1",
    description: "ACL rule blocks all traffic unexpectedly.",
    severity: "high"
  }
];

function wait(ms = 300) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function createApiError(message, status, data) {
  const error = new Error(message);
  error.status = status;
  error.data = data;
  return error;
}

function buildFriendlyErrorMessage(status, data, fallbackMessage) {
  if (status === 404) {
    return "Endpoint not found. The API path may be incorrect or the backend may not have this endpoint yet.";
  }

  if (status === 422) {
    return "Validation error. The request body or parameters may not match the backend schema.";
  }

  if (status === 500) {
    return "Backend server error. Check the FastAPI terminal for details.";
  }

  if (data?.detail) {
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((item) => `${item.loc?.join(".") || "field"}: ${item.msg}`)
        .join(" | ");
    }

    return String(data.detail);
  }

  if (data?.message) {
    return String(data.message);
  }

  return fallbackMessage;
}

async function request(path, options = {}) {
  const url = `${API_BASE_URL}${path}`;

  try {
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      },
      ...options
    });

    const contentType = response.headers.get("content-type");
    const hasJsonBody = contentType && contentType.includes("application/json");
    const data = hasJsonBody ? await response.json() : null;

    if (!response.ok) {
      const message = buildFriendlyErrorMessage(
        response.status,
        data,
        `API request failed with status ${response.status}`
      );

      throw createApiError(message, response.status, data);
    }

    return data;
  } catch (error) {
    if (error instanceof TypeError) {
      throw createApiError(`Backend API is not reachable. Please check if FastAPI is running at ${API_BASE_URL}.`,
        
        0,
        null
      );
    }

    throw error;
  }
}

function createMockLabSession({ student_id, difficulty, topology_template }) {
  const errorCount = ERROR_COUNT_BY_DIFFICULTY[difficulty] || 2;

  return {
    ...mockLabSession,
    session_id: `lab-${Date.now()}`,
    student_id,
    difficulty,
    status: "created",
    topology: {
      ...mockLabSession.topology,
      name: topology_template
    },
    injected_errors: MOCK_ERROR_POOL.slice(0, errorCount),
    cli_access: [
      {
        device_name: "r1",
        container_name: "clab-autonetlab-mock-r1",
        docker_exec_command: "docker exec -it clab-autonetlab-mock-r1 sh",
        ssh_command: ""
      },
      {
        device_name: "r2",
        container_name: "clab-autonetlab-mock-r2",
        docker_exec_command: "docker exec -it clab-autonetlab-mock-r2 sh",
        ssh_command: ""
      }
    ],
    message: "Lab session created successfully."
  };
}

function normalizeCheck(check, index) {
  const checkType =
    check.check_type ||
    check.type ||
    check.error_type ||
    check.topic ||
    "general_check";

  return {
    check_id: check.check_id || `check_${index + 1}`,
    check_type: checkType,
    topic: check.topic || checkType,
    device: check.device || check.device_name || "unknown",
    expected: check.expected ?? check.expected_value ?? "-",
    actual: check.actual ?? check.actual_value ?? "-",
    passed: Boolean(check.passed),
    message: check.message || "No check message provided.",
    related_error_type: check.related_error_type || check.code || checkType
  };
}

function normalizeRecommendation(recommendation, index) {
  if (typeof recommendation === "string") {
    return {
      topic: `Recommendation ${index + 1}`,
      priority: "medium",
      message: recommendation,
      related_error_type: "general"
    };
  }

  return {
    topic: recommendation.topic || `Recommendation ${index + 1}`,
    priority: recommendation.priority || "medium",
    message: recommendation.message || String(recommendation),
    related_error_type:
      recommendation.related_error_type ||
      recommendation.error_type ||
      recommendation.check_type ||
      "general"
  };
}

function normalizeCliAccess(cli, index) {
  return {
    device_name:
      cli.device_name ||
      cli.device ||
      cli.device_id ||
      `device-${index + 1}`,
    container_name:
      cli.container_name ||
      cli.container ||
      cli.container_id ||
      "-",
    docker_exec_command:
      cli.docker_exec_command ||
      cli.command ||
      cli.exec_command ||
      "",
    ssh_command:
      cli.ssh_command ||
      cli.ssh ||
      ""
  };
}

function normalizeValidationResult(result) {
  const checks = Array.isArray(result?.checks)
    ? result.checks.map((check, index) => normalizeCheck(check, index))
    : [];

  const passedChecks =
    result?.passed_checks ??
    result?.passed_check_count ??
    checks.filter((check) => check.passed).length;

  const totalChecks =
    result?.total_checks ??
    result?.total_check_count ??
    checks.length;

  const failedChecks =
    result?.failed_checks ??
    Math.max(totalChecks - passedChecks, 0);

  const passed =
    typeof result?.passed === "boolean"
      ? result.passed
      : String(result?.status || "").toUpperCase() === "PASS";

  const rawRecommendations =
    result?.recommendations ||
    result?.recommendation ||
    [];

  const recommendations = Array.isArray(rawRecommendations)
    ? rawRecommendations.map((item, index) =>
        normalizeRecommendation(item, index)
      )
    : [normalizeRecommendation(rawRecommendations, 0)];

  const rawCliAccess = result?.cli_access || [];

  return {
    ...result,
    session_id: result?.session_id,
    status: passed ? "PASS" : "FAIL",
    passed,
    score: result?.score ?? 0,
    difficulty: result?.difficulty || "-",
    passed_checks: passedChecks,
    failed_checks: failedChecks,
    total_checks: totalChecks,
    checks,
    recommendations,
    cli_access: Array.isArray(rawCliAccess)
      ? rawCliAccess.map((cli, index) => normalizeCliAccess(cli, index))
      : []
  };
}

export async function getDifficulties() {
  if (USE_MOCK_API) {
    await wait();
    return mockDifficulties;
  }

  return request("/meta/difficulties");
}

export async function createSession({
  student_id = "muhammed",
  difficulty = "easy",
  topology_template = "basic-two-router"
} = {}) {
  if (USE_MOCK_API) {
    await wait();

    return createMockLabSession({
      student_id,
      difficulty,
      topology_template
    });
  }

  return request("/labs", {
    method: "POST",
    body: JSON.stringify({
      student_id,
      difficulty,
      topology_template
    })
  });
}

export async function getSession(sessionId) {
  if (!sessionId) {
    throw new Error("sessionId is required.");
  }

  if (USE_MOCK_API) {
    await wait();

    return {
      ...mockLabSession,
      session_id: sessionId || mockLabSession.session_id
    };
  }

  return request(`/labs/${sessionId}`);
}

export async function getTopology(sessionId) {
  const session = await getSession(sessionId);

  return {
    session_id: session.session_id,
    topology: session.topology || null,
    injected_errors: session.injected_errors || [],
    cli_access: session.cli_access || []
  };
}

export async function deploySession(sessionId) {
  if (!sessionId) {
    throw new Error("sessionId is required.");
  }

  if (USE_MOCK_API) {
    await wait();

    return {
      session_id: sessionId,
      status: "deployed",
      message: "MOCK: Topology deployed successfully."
    };
  }

  return request(`/labs/${sessionId}/deploy`, {
    method: "POST"
  });
}

export async function destroySession(sessionId) {
  if (!sessionId) {
    throw new Error("sessionId is required.");
  }

  if (USE_MOCK_API) {
    await wait();

    return {
      session_id: sessionId,
      status: "destroyed",
      message: "MOCK: Topology destroyed successfully."
    };
  }

  return request(`/labs/${sessionId}/destroy`, {
    method: "POST"
  });
}

export async function validateSession(sessionId) {
  if (!sessionId) {
    throw new Error("sessionId is required.");
  }

  if (USE_MOCK_API) {
    await wait(600);

    return normalizeValidationResult({
      ...mockValidationResult,
      session_id: sessionId || mockValidationResult.session_id,
      status: "validated"
    });
  }

  const result = await request(`/labs/${sessionId}/validate`, {
    method: "POST"
  });

  return normalizeValidationResult(result);
}

export async function getValidationResult(sessionId) {
  if (!sessionId) {
    throw new Error("sessionId is required.");
  }

  if (USE_MOCK_API) {
    return validateSession(sessionId);
  }

  try {
    const result = await request(`/labs/${sessionId}/validation-result`);
    return normalizeValidationResult(result);
  } catch (error) {
    if (error.status === 404) {
      return validateSession(sessionId);
    }

    throw error;
  }
}

export async function getCliAccess(sessionId) {
  if (!sessionId) {
    throw new Error("sessionId is required.");
  }

  if (USE_MOCK_API) {
    await wait();

    const session = createMockLabSession({
      student_id: "muhammed",
      difficulty: "easy",
      topology_template: "basic-two-router"
    });

    return session.cli_access.map((cli, index) =>
      normalizeCliAccess(cli, index)
    );
  }

  try {
    const result = await request(`/labs/${sessionId}/cli`);
    const cliAccess = result?.cli_access || result || [];

    return Array.isArray(cliAccess)
      ? cliAccess.map((cli, index) => normalizeCliAccess(cli, index))
      : [];
  } catch (error) {
    if (error.status === 404) {
      const session = await getSession(sessionId);
      const cliAccess = session.cli_access || [];

      return Array.isArray(cliAccess)
        ? cliAccess.map((cli, index) => normalizeCliAccess(cli, index))
        : [];
    }

    throw error;
  }
}

export async function getRecommendations(sessionId) {
  if (!sessionId) {
    throw new Error("sessionId is required.");
  }

  if (USE_MOCK_API) {
    const result = await validateSession(sessionId);
    return result.recommendations;
  }

  try {
    const result = await request(`/labs/${sessionId}/recommendations`);
    const recommendations = result?.recommendations || result || [];

    return Array.isArray(recommendations)
      ? recommendations.map((item, index) => normalizeRecommendation(item, index))
      : [normalizeRecommendation(recommendations, 0)];
  } catch (error) {
    if (error.status === 404) {
      const result = await validateSession(sessionId);
      return result.recommendations;
    }

    throw error;
  }
}

// Backward-compatible aliases.
// Sprint 1 component/bileşenleri eski isimleri kullanıyorsa kırılmasın diye bırakıyoruz.
export const createLab = createSession;
export const getLab = getSession;
export const deployLab = deploySession;
export const destroyLab = destroySession;
export const validateLab = validateSession;