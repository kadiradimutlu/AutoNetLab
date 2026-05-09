import mockDifficulties from "../data/mock_difficulties.json";
import mockLabSession from "../data/mock_lab_session.json";
import mockValidationResult from "../data/mock_validation_result_backend.json";

const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API !== "false";
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1"
).replace(/\/$/, "");

const DEFAULT_STUDENT_HINTS = [
  "Check IP addressing and subnet masks.",
  "Verify interface status before testing connectivity.",
  "Review routing and default gateway configuration.",
  "Compare addressing, interfaces, and routing step by step across the topology."
];

const MOCK_INSTRUCTOR_SUMMARY = {
  success: true,
  total_sessions: 12,
  completed_sessions: 9,
  active_sessions: 3,
  passed_sessions: 6,
  average_score: 74.44,
  pass_rate: 66.67,
  message: "MOCK: Instructor analytics summary loaded."
};

const MOCK_DIFFICULTY_DISTRIBUTION = {
  success: true,
  distribution: [
    {
      difficulty: "easy",
      session_count: 4,
      completed_count: 4,
      average_score: 86.25
    },
    {
      difficulty: "medium",
      session_count: 5,
      completed_count: 3,
      average_score: 72.33
    },
    {
      difficulty: "hard",
      session_count: 3,
      completed_count: 2,
      average_score: 58.5
    }
  ],
  message: "MOCK: Difficulty distribution loaded."
};

const MOCK_TOPIC_WEAKNESSES = {
  success: true,
  topic_weaknesses: [
    {
      topic: "ip_addressing",
      label: "IP Addressing",
      fail_count: 5,
      attempt_count: 9,
      failure_rate: 55.56,
      average_score: 64.25,
      severity: "high"
    },
    {
      topic: "routing",
      label: "Routing",
      fail_count: 3,
      attempt_count: 8,
      failure_rate: 37.5,
      average_score: 71.5,
      severity: "medium"
    },
    {
      topic: "interface_status",
      label: "Interface Status",
      fail_count: 1,
      attempt_count: 6,
      failure_rate: 16.67,
      average_score: 84,
      severity: "low"
    }
  ],
  message: "MOCK: Topic weaknesses loaded."
};

const MOCK_RECENT_SESSIONS = {
  success: true,
  recent_sessions: [
    {
      session_id: "lab-demo-001",
      student_id: "muhammed",
      difficulty: "medium",
      status: "validated",
      score: 75,
      passed: false,
      created_at: "2026-05-09T10:00:00",
      completed_at: "2026-05-09T10:18:00"
    },
    {
      session_id: "lab-demo-002",
      student_id: "kadir",
      difficulty: "easy",
      status: "validated",
      score: 90,
      passed: true,
      created_at: "2026-05-09T09:30:00",
      completed_at: "2026-05-09T09:42:00"
    },
    {
      session_id: "lab-demo-003",
      student_id: "muhammed",
      difficulty: "hard",
      status: "deployed",
      score: null,
      passed: null,
      created_at: "2026-05-09T08:50:00",
      completed_at: null
    }
  ],
  message: "MOCK: Recent sessions loaded."
};

export function isMockApiEnabled() {
  return USE_MOCK_API;
}

function sanitizeStudentSession(session) {
  if (!session || typeof session !== "object") {
    return session;
  }

  const safeSession = {
    ...session
  };

  delete safeSession.injected_errors;
  delete safeSession.expected_fix;
  delete safeSession.solution;
  delete safeSession.answer;
  delete safeSession.debug;

  return {
    ...safeSession,
    topology: safeSession.topology || {
      name: "basic-two-router",
      nodes: [],
      links: []
    },
    cli_access: Array.isArray(safeSession.cli_access)
      ? safeSession.cli_access
      : [],
    hints:
      Array.isArray(safeSession.hints) && safeSession.hints.length > 0
        ? safeSession.hints
        : DEFAULT_STUDENT_HINTS
  };
}

function wait(ms = 300) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getRequestMethod(options = {}) {
  return options.method || "GET";
}

function formatBackendDetail(detail) {
  if (!detail) {
    return "";
  }

  if (typeof detail === "string") {
    return detail;
  }

  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") {
          return item;
        }

        const location = Array.isArray(item.loc) ? item.loc.join(".") : "";
        const message = item.msg || item.message || JSON.stringify(item);

        return location ? `${location}: ${message}` : message;
      })
      .join(" | ");
  }

  if (typeof detail === "object") {
    return detail.message || detail.error || JSON.stringify(detail);
  }

  return String(detail);
}

function getRawErrorMessage(data, fallbackMessage) {
  return (
    formatBackendDetail(data?.detail) ||
    formatBackendDetail(data?.message) ||
    formatBackendDetail(data?.error) ||
    fallbackMessage
  );
}

function getFriendlyErrorMessage({ status, path, method }) {
  if (status === 0) {
    return "Backend API is not reachable. Please make sure the FastAPI server is running and the API base URL is correct.";
  }

  if (status === 400) {
    return "The request was rejected by the backend. Please check the submitted data.";
  }

  if (status === 404) {
    if (path.includes("/cli")) {
      return "CLI access information could not be found. Please check the CLI endpoint or the session data.";
    }

    if (path.includes("/instructor")) {
      return "Instructor analytics endpoint could not be found. Please make sure the Sprint 6 backend is running.";
    }

    return "Invalid session ID or endpoint not found. Please create a new lab or check the API path.";
  }

  if (status === 409) {
    return "This operation conflicts with the current session state. Please refresh the session and try again.";
  }

  if (status === 422) {
    return "The submitted data does not match the format expected by the backend. Please check the field names and request body.";
  }

  if (status >= 500) {
    if (path.includes("/deploy")) {
      return "Containerlab deploy operation failed. Please check Docker, WSL, or Containerlab setup.";
    }

    if (path.includes("/destroy")) {
      return "Containerlab destroy operation failed. Please check the running containers or Containerlab state.";
    }

    if (path.includes("/validate")) {
      return "Validation operation failed on the backend side. Please try again.";
    }

    if (path.includes("/instructor")) {
      return "Instructor analytics could not be generated on the backend side. Please check the FastAPI terminal output.";
    }

    return "An unexpected backend error occurred. Please check the FastAPI terminal output.";
  }

  return `${method} request failed. Please try again.`;
}

function createApiError({
  status,
  data,
  path,
  method,
  url,
  message,
  originalError
}) {
  const error = new Error(
    getFriendlyErrorMessage({
      status,
      path,
      method
    })
  );

  error.name = "ApiServiceError";
  error.status = status;
  error.data = data;
  error.path = path;
  error.method = method;
  error.url = url;
  error.originalError = originalError || null;
  error.technicalMessage =
    message ||
    getRawErrorMessage(data, `API request failed with status ${status}`);
  error.friendlyMessage = error.message;
  error.isApiError = true;

  return error;
}

async function parseResponseBody(response) {
  const contentType = response.headers.get("content-type") || "";
  const hasJsonBody = contentType.includes("application/json");

  if (hasJsonBody) {
    return response.json();
  }

  const text = await response.text();

  if (!text) {
    return null;
  }

  return {
    message: text
  };
}

async function request(path, options = {}) {
  const url = `${API_BASE_URL}${path}`;
  const method = getRequestMethod(options);

  try {
    const response = await fetch(url, {
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      },
      ...options
    });

    const data = await parseResponseBody(response);

    if (!response.ok) {
      throw createApiError({
        status: response.status,
        data,
        path,
        method,
        url,
        message: getRawErrorMessage(
          data,
          `API request failed with status ${response.status}`
        )
      });
    }

    return data;
  } catch (error) {
    if (error.isApiError) {
      throw error;
    }

    if (error instanceof TypeError) {
      throw createApiError({
        status: 0,
        data: null,
        path,
        method,
        url,
        message:
          "Network error, CORS error, or backend server is not reachable.",
        originalError: error
      });
    }

    throw createApiError({
      status: -1,
      data: null,
      path,
      method,
      url,
      message: error.message || "Unexpected frontend API error.",
      originalError: error
    });
  }
}

export function getErrorMessage(error, fallbackMessage = "Operation failed.") {
  return error?.friendlyMessage || error?.message || fallbackMessage;
}

export function getErrorDetails(error) {
  if (!error) {
    return "";
  }

  const details = [];

  if (error.status !== undefined && error.status !== null) {
    details.push(`Status: ${error.status}`);
  }

  if (error.method && error.path) {
    details.push(`Request: ${error.method} ${error.path}`);
  }

  if (error.technicalMessage) {
    details.push(`Detail: ${error.technicalMessage}`);
  }

  return details.join(" | ");
}

function createMockLabSession({ student_id, difficulty, topology_template }) {
  return sanitizeStudentSession({
    ...mockLabSession,
    success: true,
    session_id: `lab-${Date.now()}`,
    student_id,
    difficulty,
    status: "created",
    topology: {
      ...mockLabSession.topology,
      name: topology_template
    },
    cli_access: [
      {
        device_id: "r1",
        name: "Router 1",
        container_name: "clab-autonetlab-mock-r1",
        access_method: "docker_exec",
        command: "docker exec -it clab-autonetlab-mock-r1 sh",
        description: "Open CLI access for router r1."
      },
      {
        device_id: "r2",
        name: "Router 2",
        container_name: "clab-autonetlab-mock-r2",
        access_method: "docker_exec",
        command: "docker exec -it clab-autonetlab-mock-r2 sh",
        description: "Open CLI access for router r2."
      }
    ],
    hints: DEFAULT_STUDENT_HINTS,
    message: "Lab session created successfully."
  });
}

function normalizeValidationResult(result) {
  const checks = Array.isArray(result?.checks) ? result.checks : [];
  const passedChecks = checks.filter((check) => check.passed).length;
  const totalChecks = checks.length;

  const recommendations =
    result?.recommendations || result?.recommendation || [];

  return {
    ...result,
    passed: Boolean(result?.passed),
    score: result?.score ?? 0,
    checks,
    passed_checks: result?.passed_checks ?? passedChecks,
    total_checks: result?.total_checks ?? totalChecks,
    recommendations: Array.isArray(recommendations)
      ? recommendations
      : [recommendations].filter(Boolean)
  };
}

function normalizeCliAccess(cli, index) {
  return {
    device_name:
      cli.device_name ||
      cli.name ||
      cli.device ||
      cli.device_id ||
      cli.container_name ||
      `device-${index + 1}`,
    container_name:
      cli.container_name ||
      cli.container ||
      cli.container_id ||
      "-",
    access_method:
      cli.access_method ||
      cli.method ||
      "docker_exec",
    docker_exec_command:
      cli.docker_exec_command ||
      cli.command ||
      cli.exec_command ||
      "",
    ssh_command:
      cli.ssh_command ||
      cli.ssh ||
      "",
    description:
      cli.description ||
      ""
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

  const result = await request("/labs", {
    method: "POST",
    body: JSON.stringify({
      student_id,
      difficulty,
      topology_template
    })
  });

  return sanitizeStudentSession(result);
}

export async function getSession(sessionId) {
  if (!sessionId) {
    throw new Error("sessionId is required.");
  }

  if (USE_MOCK_API) {
    await wait();

    return sanitizeStudentSession({
      ...mockLabSession,
      session_id: sessionId || mockLabSession.session_id
    });
  }

  const result = await request(`/labs/${sessionId}`);

  return sanitizeStudentSession(result);
}

export async function getTopology(sessionId) {
  const session = await getSession(sessionId);

  return {
    session_id: session.session_id,
    topology: session.topology || null,
    cli_access: session.cli_access || [],
    hints: session.hints || DEFAULT_STUDENT_HINTS
  };
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

    return (session.cli_access || []).map((cli, index) =>
      normalizeCliAccess(cli, index)
    );
  }

  try {
    const result = await request(`/labs/${sessionId}/cli`);
    const cliAccess = result?.cli_access || result?.items || result || [];

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

export async function getInstructorSummary() {
  if (USE_MOCK_API) {
    await wait();

    return MOCK_INSTRUCTOR_SUMMARY;
  }

  return request("/instructor/analytics/summary");
}

export async function getDifficultyDistribution() {
  if (USE_MOCK_API) {
    await wait();

    return MOCK_DIFFICULTY_DISTRIBUTION;
  }

  return request("/instructor/analytics/difficulty-distribution");
}

export async function getTopicWeaknesses() {
  if (USE_MOCK_API) {
    await wait();

    return MOCK_TOPIC_WEAKNESSES;
  }

  return request("/instructor/analytics/topic-weaknesses");
}

export async function getRecentSessions(limit = 10) {
  const safeLimit = Math.min(Math.max(Number(limit) || 10, 1), 50);

  if (USE_MOCK_API) {
    await wait();

    return {
      ...MOCK_RECENT_SESSIONS,
      recent_sessions: MOCK_RECENT_SESSIONS.recent_sessions.slice(0, safeLimit)
    };
  }

  return request(`/instructor/sessions/recent?limit=${safeLimit}`);
}

// Backward-compatible aliases.
// Sprint 1 components may still use the old function names.
export const createLab = createSession;
export const getLab = getSession;
export const deployLab = deploySession;
export const destroyLab = destroySession;
export const validateLab = validateSession;