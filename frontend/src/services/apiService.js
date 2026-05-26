import mockDifficulties from "../data/mock_difficulties.json";
import mockLabSession from "../data/mock_lab_session.json";
import mockValidationResult from "../data/mock_validation_result_backend.json";
import mockRecommendation from "../data/mock_recommendation.json";

const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API !== "false";
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "/api/v1"
).replace(/\/$/, "");

const AUTH_STORAGE_KEY = "autonetlab_auth_state";

const DEMO_AUTH_USERS = {
  student: {
    password: "student123",
    access_token: "demo-student-token",
    token_type: "bearer",
    user: {
      username: "student",
      display_name: "Student Demo User",
      role: "student",
      student_id: "demo-student"
    },
    message: "Demo student login successful."
  },
  instructor: {
    password: "instructor123",
    access_token: "demo-instructor-token",
    token_type: "bearer",
    user: {
      username: "instructor",
      display_name: "Instructor Demo User",
      role: "instructor",
      student_id: null
    },
    message: "Demo instructor login successful."
  }
};

function canUseLocalStorage() {
  return typeof window !== "undefined" && Boolean(window.localStorage);
}

function readAuthState() {
  if (!canUseLocalStorage()) {
    return null;
  }

  try {
    const rawAuthState = window.localStorage.getItem(AUTH_STORAGE_KEY);

    if (!rawAuthState) {
      return null;
    }

    return JSON.parse(rawAuthState);
  } catch (error) {
    console.error("Stored auth state could not be parsed.", error);
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
}

function writeAuthState(authState) {
  if (!canUseLocalStorage()) {
    return;
  }

  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authState));
}

function clearAuthState() {
  if (!canUseLocalStorage()) {
    return;
  }

  window.localStorage.removeItem(AUTH_STORAGE_KEY);
}

function normalizeRole(role) {
  return String(role || "student").toLowerCase() === "instructor"
    ? "instructor"
    : "student";
}

function normalizeAuthResponse(payload) {
  const safePayload = payload && typeof payload === "object" ? payload : {};
  const user = safePayload.user && typeof safePayload.user === "object"
    ? safePayload.user
    : safePayload;

  const normalizedUser = {
    username: user.username || user.name || "student",
    display_name:
      user.display_name ||
      user.displayName ||
      user.full_name ||
      user.username ||
      "AutoNetLab User",
    role: normalizeRole(user.role),
    student_id: user.student_id || user.studentId || null
  };

  return {
    success: safePayload.success ?? true,
    access_token:
      safePayload.access_token ||
      safePayload.token ||
      safePayload.accessToken ||
      "",
    token_type: safePayload.token_type || safePayload.tokenType || "bearer",
    user: normalizedUser,
    message: safePayload.message || ""
  };
}

export function getStoredAuth() {
  return readAuthState();
}

export function getAuthToken() {
  return readAuthState()?.access_token || "";
}

function getAuthHeaders() {
  const token = getAuthToken();

  if (!token) {
    return {};
  }

  return {
    Authorization: `Bearer ${token}`
  };
}

export function logoutUser() {
  clearAuthState();
}

function createMockAuthState(username, password) {
  const normalizedUsername = String(username || "").trim().toLowerCase();
  const demoUser = DEMO_AUTH_USERS[normalizedUsername];

  if (!demoUser || demoUser.password !== password) {
    throw new Error("Invalid demo username or password.");
  }

  const authState = normalizeAuthResponse({
    ...demoUser,
    user: {
      ...demoUser.user
    }
  });

  writeAuthState(authState);
  return authState;
}

export async function loginUser({ username, password }) {
  clearAuthState();

  if (USE_MOCK_API) {
    await wait();
    return createMockAuthState(username, password);
  }

  const result = await request("/auth/login", {
    method: "POST",
    body: JSON.stringify({
      username,
      password
    })
  });

  const authState = normalizeAuthResponse(result);
  writeAuthState(authState);
  return authState;
}

export async function registerUser({
  username,
  password,
  display_name,
  email,
  student_id
}) {
  if (USE_MOCK_API) {
    await wait();

    const normalizedUsername = String(username || "").trim().toLowerCase();

    if (DEMO_AUTH_USERS[normalizedUsername]) {
      throw createApiError({
        status: 409,
        data: {
          success: false,
          error_code: "USERNAME_ALREADY_EXISTS",
          message: "This username already exists.",
          suggestion: "Choose a different username for the demo registration."
        },
        path: "/auth/register",
        method: "POST",
        url: "mock://auth/register"
      });
    }

    return {
      success: true,
      user: {
        username,
        display_name: display_name || username,
        role: "student",
        student_id: student_id || username
      },
      message: "MOCK: Registration successful."
    };
  }

  return request("/auth/register", {
    method: "POST",
    body: JSON.stringify({
      username,
      password,
      display_name,
      email,
      student_id
    })
  });
}

export async function getCurrentUser() {
  const storedAuthState = readAuthState();

  if (!storedAuthState?.access_token) {
    return null;
  }

  if (USE_MOCK_API) {
    await wait(150);
    return storedAuthState;
  }

  try {
    const result = await request("/auth/me");
    const authState = normalizeAuthResponse({
      ...storedAuthState,
      user: result?.user || result
    });

    authState.access_token = storedAuthState.access_token;
    authState.token_type = storedAuthState.token_type || authState.token_type;

    writeAuthState(authState);
    return authState;
  } catch (error) {
    if (error.status === 401 || error.status === 403) {
      clearAuthState();
    }

    throw error;
  }
}

const MOCK_CLI_ACCESS_MODES = {
  success: true,
  current_mode: "browser_cli_mvp",
  default_mode: "browser_cli_mvp",
  fallback_mode: "local_docker_exec_demo_fallback",
  websocket: {
    path_template: "/api/v1/labs/{session_id}/cli/ws/{device_id}",
    auth_query_param: "token"
  },
  message: "MOCK: CLI access modes loaded."
};

const MOCK_WEB_CLI_READINESS = {
  success: true,
  session_id: "lab-demo-001",
  current_mode: "browser_cli_mvp",
  lab_status: "deployed",
  lab_deployed: true,
  ready: true,
  devices: [
    {
      device_id: "r1",
      container_name: "clab-autonetlab-mock-r1",
      docker_available: true,
      container_running: true,
      ready: true,
      error_code: null,
      message: "MOCK: Device r1 is ready for Web CLI."
    },
    {
      device_id: "r2",
      container_name: "clab-autonetlab-mock-r2",
      docker_available: true,
      container_running: true,
      ready: true,
      error_code: null,
      message: "MOCK: Device r2 is ready for Web CLI."
    }
  ],
  error_code: null,
  message: "MOCK: Web CLI readiness check completed."
};

const MOCK_RUNTIME_READINESS = {
  success: true,
  ready: true,
  platform: "Linux",
  platform_release: "Ubuntu demo environment",
  recommended_backend_environment: "Linux VM or WSL2 Ubuntu with Docker and Containerlab",
  project_root: "/opt/autonetlab",
  templates_dir: "/opt/autonetlab/containerlab/templates",
  templates_dir_exists: true,
  generated_dir: "/opt/autonetlab/containerlab/generated",
  generated_dir_exists: true,
  docker_available: true,
  docker_version: "MOCK Docker 29.x",
  docker_ps_ok: true,
  containerlab_available: true,
  containerlab_version: "MOCK containerlab 0.75.0",
  current_mode: "browser_cli_mvp",
  fallback_mode: "local_docker_exec_demo_fallback",
  checks: [
    {
      name: "Docker command",
      ok: true,
      message: "Docker command is available."
    },
    {
      name: "Docker daemon",
      ok: true,
      message: "Docker daemon responds to docker ps."
    },
    {
      name: "Containerlab command",
      ok: true,
      message: "Containerlab command is available."
    },
    {
      name: "Templates directory",
      ok: true,
      message: "Containerlab templates directory exists."
    }
  ],
  message: "MOCK: Demo runtime environment is ready."
};

const MOCK_DATABASE_READINESS = {
  success: true,
  ready: true,
  database_url: "postgresql+psycopg://***:***@127.0.0.1:5432/autonetlab",
  database_engine: "postgresql",
  message: "MOCK: Database connection check succeeded.",
  error: null
};

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

const MOCK_INSTRUCTOR_STUDENTS = {
  success: true,
  students: [
    {
      student_id: "demo-student",
      total_sessions: 8,
      completed_sessions: 6,
      active_sessions: 1,
      average_score: 76.5,
      pass_rate: 66.7,
      last_activity_at: "2026-05-14T12:30:00"
    },
    {
      student_id: "muhammed",
      total_sessions: 5,
      completed_sessions: 4,
      active_sessions: 0,
      average_score: 82.25,
      pass_rate: 75,
      last_activity_at: "2026-05-13T16:20:00"
    },
    {
      student_id: "kadir",
      total_sessions: 4,
      completed_sessions: 3,
      active_sessions: 1,
      average_score: 68,
      pass_rate: 33.3,
      last_activity_at: "2026-05-12T09:45:00"
    }
  ],
  message: "MOCK: Instructor student list loaded."
};

const MOCK_STUDENT_DETAIL = {
  "demo-student": {
    summary: {
      success: true,
      student_id: "demo-student",
      total_sessions: 8,
      completed_sessions: 6,
      active_sessions: 1,
      passed_sessions: 4,
      average_score: 76.5,
      pass_rate: 66.7,
      first_seen_at: "2026-05-01T09:00:00",
      last_activity_at: "2026-05-14T12:30:00",
      message: "MOCK: Student summary loaded."
    },
    sessions: [
      {
        session_id: "lab-demo-301",
        student_id: "demo-student",
        difficulty: "easy",
        status: "validated",
        score: 90,
        passed: true,
        created_at: "2026-05-10T09:00:00",
        completed_at: "2026-05-10T09:18:00"
      },
      {
        session_id: "lab-demo-302",
        student_id: "demo-student",
        difficulty: "medium",
        status: "validated",
        score: 70,
        passed: false,
        created_at: "2026-05-12T11:20:00",
        completed_at: "2026-05-12T11:47:00"
      },
      {
        session_id: "lab-demo-303",
        student_id: "demo-student",
        difficulty: "hard",
        status: "deployed",
        score: null,
        passed: null,
        created_at: "2026-05-14T12:30:00",
        completed_at: null
      }
    ],
    topic_weaknesses: [
      {
        topic: "static_routing",
        label: "Static Routing",
        fail_count: 3,
        attempt_count: 6,
        failure_rate: 50,
        average_score: 62,
        severity: "high"
      },
      {
        topic: "ip_addressing",
        label: "IP Addressing",
        fail_count: 2,
        attempt_count: 7,
        failure_rate: 28.6,
        average_score: 74,
        severity: "medium"
      }
    ],
    score_trend: [
      {
        session_id: "lab-demo-299",
        difficulty: "easy",
        status: "validated",
        score: 65,
        passed: false,
        created_at: "2026-05-08T10:00:00",
        completed_at: "2026-05-08T10:18:00"
      },
      {
        session_id: "lab-demo-301",
        difficulty: "easy",
        status: "validated",
        score: 90,
        passed: true,
        created_at: "2026-05-10T09:00:00",
        completed_at: "2026-05-10T09:18:00"
      },
      {
        session_id: "lab-demo-302",
        difficulty: "medium",
        status: "validated",
        score: 70,
        passed: false,
        created_at: "2026-05-12T11:20:00",
        completed_at: "2026-05-12T11:47:00"
      }
    ]
  }
};

const MOCK_LAB_HISTORY = {
  success: true,
  sessions: [
    {
      success: true,
      session_id: "lab-demo-001",
      student_id: "demo-student",
      difficulty: "easy",
      status: "validated",
      score: 90,
      passed: true,
      created_at: "2026-05-10T09:00:00+00:00",
      completed_at: "2026-05-10T09:18:00+00:00",
      topology_summary: {
        name: "autonetlab-lab-demo-001",
        node_count: 2,
        link_count: 1,
        devices: ["r1", "r2"]
      },
      topology: {},
      cli_access: [],
      hints: [],
      message: "MOCK: Lab session listed successfully."
    },
    {
      success: true,
      session_id: "lab-demo-hard-004",
      student_id: "demo-student",
      difficulty: "hard",
      status: "deployed",
      score: null,
      passed: null,
      created_at: "2026-05-14T12:30:00+00:00",
      completed_at: null,
      topology_summary: {
        name: "autonetlab-lab-demo-hard-004",
        node_count: 4,
        link_count: 4,
        devices: ["r1", "r2", "r3", "r4"]
      },
      topology: {},
      cli_access: [],
      hints: [],
      message: "MOCK: Lab session listed successfully."
    }
  ],
  count: 2,
  message: "MOCK: Lab sessions retrieved successfully."
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

function normalizeRecommendationSource(source) {
  const normalizedSource = String(source || "rule_based").toLowerCase();

  if (normalizedSource === "ml_prototype") {
    return "ml_prototype";
  }

  if (normalizedSource === "hybrid") {
    return "hybrid";
  }

  return "rule_based";
}

function normalizeRecommendationConfidence(confidence) {
  if (confidence === undefined || confidence === null || confidence === "") {
    return null;
  }

  const numericConfidence = Number(confidence);

  if (Number.isNaN(numericConfidence)) {
    return null;
  }

  if (numericConfidence > 1) {
    return Math.min(Math.max(numericConfidence, 0), 100) / 100;
  }

  return Math.min(Math.max(numericConfidence, 0), 1);
}

function normalizeRecommendationList(value) {
  if (!value) {
    return [];
  }

  if (Array.isArray(value)) {
    return value.filter(Boolean);
  }

  return [value];
}

function normalizeRecommendationItem(item, index, parentSource = "rule_based") {
  if (typeof item === "string") {
    return {
      id: `recommendation-${index + 1}`,
      topic: `recommendation_${index + 1}`,
      label: `Recommendation ${index + 1}`,
      reason: item,
      explanation: "This recommendation was generated from the validation result.",
      priority: "medium",
      confidence: null,
      source: normalizeRecommendationSource(parentSource),
      fallback_used: false,
      next_actions: [],
      related_failed_checks: []
    };
  }

  if (!item || typeof item !== "object") {
    return {
      id: `recommendation-${index + 1}`,
      topic: `recommendation_${index + 1}`,
      label: `Recommendation ${index + 1}`,
      reason: "No recommendation detail is available.",
      explanation: "Run validation again if this recommendation looks incomplete.",
      priority: "medium",
      confidence: null,
      source: normalizeRecommendationSource(parentSource),
      fallback_used: false,
      next_actions: [],
      related_failed_checks: []
    };
  }

  const topic = item.topic || item.title || `recommendation_${index + 1}`;

  return {
    id: item.id || `${topic}-${index}`,
    topic,
    label: item.label || item.topic_label || item.display_name || String(topic).replace(/_/g, " "),
    reason: item.reason || item.message || item.description || "This topic was selected based on the validation result.",
    explanation: item.explanation || item.details || item.text || "Review this topic before attempting a harder lab.",
    priority: String(item.priority || item.severity || item.level || "medium").toLowerCase(),
    confidence: normalizeRecommendationConfidence(item.confidence),
    source: normalizeRecommendationSource(item.source || parentSource),
    fallback_used: Boolean(item.fallback_used),
    next_actions: normalizeRecommendationList(item.next_actions || item.nextActions || item.actions),
    related_failed_checks: normalizeRecommendationList(
      item.related_failed_checks || item.failed_checks || item.relatedChecks
    )
  };
}

function normalizeRecommendationPayload(payload, sessionId = "") {
  const safePayload = payload && typeof payload === "object" ? payload : {};
  const source = normalizeRecommendationSource(safePayload.source);
  const recommendations = normalizeRecommendationList(safePayload.recommendations).map(
    (item, index) => normalizeRecommendationItem(item, index, source)
  );

  return {
    success: safePayload.success ?? true,
    session_id: safePayload.session_id || sessionId || "",
    status: safePayload.status || "",
    score: safePayload.score ?? null,
    passed: safePayload.passed ?? null,
    source,
    fallback_used: Boolean(safePayload.fallback_used),
    recommendations,
    message: safePayload.message || ""
  };
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

function getFriendlyErrorMessage({ status, path, method, data }) {
  const detailObject =
    data?.detail && typeof data.detail === "object" && !Array.isArray(data.detail)
      ? data.detail
      : {};
  const backendMessage =
    formatBackendDetail(data?.message) ||
    formatBackendDetail(detailObject.message);
  const backendSuggestion =
    formatBackendDetail(data?.suggestion) ||
    formatBackendDetail(detailObject.suggestion);
  const backendErrorCode =
    data?.error_code ||
    data?.code ||
    detailObject.error_code ||
    detailObject.code ||
    "";

  const backendDetail = formatBackendDetail(data?.detail);
  const cleanupRequired = Boolean(
    data?.cleanup_required === true ||
      detailObject.cleanup_required === true ||
      data?.requires_cleanup === true ||
      detailObject.requires_cleanup === true ||
      backendDetail.toLowerCase().includes("runtime cleanup") ||
      backendMessage.toLowerCase().includes("runtime cleanup")
  );

  if (cleanupRequired) {
    return (
      backendDetail ||
      backendMessage ||
      "You have a lab that requires runtime cleanup. Clean it up before creating a new lab."
    );
  }

  if (backendMessage) {
    return backendMessage;
  }

  if (backendErrorCode === "INVALID_CREDENTIALS") {
    return "Invalid username or password.";
  }

  if (backendErrorCode === "USERNAME_ALREADY_EXISTS") {
    return "This username already exists. Please choose a different username.";
  }

  if (backendErrorCode === "AUTHENTICATION_REQUIRED") {
    return "Login is required for this endpoint.";
  }

  if (backendErrorCode === "LAB_OWNERSHIP_FORBIDDEN") {
    return "This lab belongs to a different student account.";
  }

  if (backendErrorCode === "INSTRUCTOR_ROLE_REQUIRED") {
    return "Instructor access is required for this page.";
  }

  if (backendErrorCode === "LAB_SESSION_NOT_FOUND") {
    return "Lab session was not found.";
  }

  if (backendErrorCode === "ACTIVE_LAB_ALREADY_EXISTS") {
    return "You already have an active lab. Finish or close it before creating a new one.";
  }

  if (status === 0) {
    return "The application service is not reachable. Please check the server connection and API base URL.";
  }

  if (status === 400) {
    return "The request was rejected by the application service. Please check the submitted data.";
  }

  if (status === 401) {
    return "Your session is not authorized. Please sign in again.";
  }

  if (status === 403) {
    return "This user role is not allowed to access the requested page or endpoint.";
  }

  if (status === 404) {
    if (path.includes("/cli")) {
      return "CLI access information could not be found. Please check the CLI endpoint or the session data.";
    }

    if (path.includes("/instructor")) {
      return "Instructor analytics endpoint could not be found. Please make sure the analytics service is available.";
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
      return "Validation operation failed. Please try again.";
    }

    if (path.includes("/instructor")) {
      return "Instructor analytics could not be generated. Please check the application service logs.";
    }

    return "An unexpected server error occurred. Please check the application service logs.";
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
      method,
      data
    })
  );

  error.name = "ApiServiceError";
  error.status = status;
  error.data = data;
  const detailObject =
    data?.detail && typeof data.detail === "object" && !Array.isArray(data.detail)
      ? data.detail
      : {};

  error.errorCode =
    data?.error_code ||
    data?.code ||
    detailObject.error_code ||
    detailObject.code ||
    "";
  error.suggestion = data?.suggestion || detailObject.suggestion || "";
  error.activeSessionId =
    data?.active_session_id ||
    data?.activeSessionId ||
    detailObject.active_session_id ||
    detailObject.activeSessionId ||
    "";
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
  const { headers: optionHeaders = {}, ...fetchOptions } = options;

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
        ...optionHeaders
      }
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
          "Network error, CORS error, or application service is not reachable.",
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

  if (error.errorCode) {
    details.push(`Error code: ${error.errorCode}`);
  }

  if (error.suggestion) {
    details.push(`Suggestion: ${error.suggestion}`);
  }

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
    cli_access_mode: "local_docker_exec_demo",
    scenario_overview: {
      summary:
        difficulty === "hard"
          ? "This hard scenario combines multiple troubleshooting topics while keeping exact injected errors hidden from the student view."
          : "This scenario provides troubleshooting guidance without revealing the expected solution.",
      topics:
        difficulty === "hard"
          ? ["IP Addressing", "Routing", "Interface Status", "Connectivity"]
          : ["IP Addressing", "Interface Status"],
      hints: DEFAULT_STUDENT_HINTS
    },
    topology: {
      ...mockLabSession.topology,
      name: topology_template
    },
    cli_access: [
      {
        device_id: "r1",
        name: "Router 1",
        container_name: "clab-autonetlab-mock-r1",
        access_method: "local_docker_exec_demo",
        mode: "local_docker_exec_demo",
        command: "docker exec -it clab-autonetlab-mock-r1 sh",
        description: "Open CLI access for router r1."
      },
      {
        device_id: "r2",
        name: "Router 2",
        container_name: "clab-autonetlab-mock-r2",
        access_method: "local_docker_exec_demo",
        mode: "local_docker_exec_demo",
        command: "docker exec -it clab-autonetlab-mock-r2 sh",
        description: "Open CLI access for router r2."
      }
    ],
    hints: DEFAULT_STUDENT_HINTS,
    message: "Lab session created successfully."
  });
}

function normalizeCheckPassed(check) {
  const status = String(check?.status || "").toLowerCase();

  if (status.includes("pass") || status === "success") {
    return true;
  }

  if (status.includes("fail") || status === "error") {
    return false;
  }

  return Boolean(check?.passed);
}

function normalizeValidationCheck(check, index) {
  const safeCheck = check && typeof check === "object" ? check : {};
  const passed = normalizeCheckPassed(safeCheck);

  return {
    ...safeCheck,
    check_id: safeCheck.check_id || safeCheck.id || `check-${index + 1}`,
    topic: safeCheck.topic || safeCheck.category || "General",
    description:
      safeCheck.description ||
      safeCheck.message ||
      safeCheck.name ||
      `Validation check ${index + 1}`,
    status: safeCheck.status || (passed ? "passed" : "failed"),
    passed,
    points: safeCheck.points ?? safeCheck.score ?? 0,
    max_points: safeCheck.max_points ?? safeCheck.maxPoints ?? 0,
    message:
      safeCheck.message ||
      (passed
        ? "This validation check passed."
        : "This validation check failed. Review the topic and try again."),
    hint:
      safeCheck.hint ||
      safeCheck.student_hint ||
      "Review this topic and re-check the device configuration."
  };
}

function normalizeValidationResult(result, recommendationPayload = null) {
  const checks = Array.isArray(result?.checks)
    ? result.checks.map((check, index) => normalizeValidationCheck(check, index))
    : [];
  const passedChecks = checks.filter((check) => check.passed).length;
  const totalChecks = checks.length;
  const computedScoreMax = checks.reduce(
    (total, check) => total + Number(check.max_points || 0),
    0
  );
  const computedScoreValue = checks.reduce(
    (total, check) => total + Number(check.points || 0),
    0
  );
  const computedScore = computedScoreMax
    ? Math.round((computedScoreValue / computedScoreMax) * 100)
    : 0;

  const fallbackRecommendationPayload = {
    success: true,
    session_id: result?.session_id || "",
    status: result?.status || "",
    score: result?.score ?? computedScore,
    passed: result?.passed ?? passedChecks === totalChecks,
    source: result?.source || "rule_based",
    fallback_used: Boolean(result?.fallback_used),
    recommendations: result?.recommendations || result?.recommendation || [],
    message: result?.message || ""
  };

  const normalizedRecommendationPayload = normalizeRecommendationPayload(
    recommendationPayload || fallbackRecommendationPayload,
    result?.session_id || ""
  );

  return {
    ...result,
    passed: result?.passed ?? passedChecks === totalChecks,
    score: result?.score ?? computedScore,
    checks,
    passed_checks: result?.passed_checks ?? passedChecks,
    total_checks: result?.total_checks ?? totalChecks,
    recommendations: normalizedRecommendationPayload.recommendations,
    recommendation_payload: normalizedRecommendationPayload,
    recommendation_source: normalizedRecommendationPayload.source,
    recommendation_fallback_used: normalizedRecommendationPayload.fallback_used,
    recommendation_message: normalizedRecommendationPayload.message
  };
}

function getCleanCliDescription(description, deviceId) {
  const rawDescription = String(description || "").trim();
  const normalizedDeviceId = deviceId || "device";

  const looksCorrupted =
    rawDescription.includes("Ã") ||
    rawDescription.includes("Ä") ||
    rawDescription.includes("Å") ||
    rawDescription.includes("Â") ||
    rawDescription.includes("�");

  if (!rawDescription || looksCorrupted) {
    return `Use this command to access ${normalizedDeviceId} from the terminal.`;
  }

  return rawDescription;
}

function normalizeCliAccess(cli, index) {
  const safeCli = cli && typeof cli === "object" ? cli : {};
  const deviceId =
    safeCli.device_id ||
    safeCli.deviceId ||
    safeCli.device ||
    safeCli.name ||
    `device-${index + 1}`;

  return {
    device_id: deviceId,
    device_name:
      safeCli.device_name ||
      safeCli.name ||
      safeCli.device ||
      safeCli.device_id ||
      safeCli.container_name ||
      `device-${index + 1}`,
    container_name:
      safeCli.container_name ||
      safeCli.container ||
      safeCli.container_id ||
      "-",
    access_method:
      safeCli.access_method ||
      safeCli.method ||
      safeCli.mode ||
      "local_docker_exec_demo",
    mode:
      safeCli.mode ||
      safeCli.cli_mode ||
      safeCli.access_mode ||
      safeCli.access_method ||
      "local_docker_exec_demo",
    docker_exec_command:
      safeCli.docker_exec_command ||
      safeCli.command ||
      safeCli.exec_command ||
      "",
    ssh_command:
      safeCli.ssh_command ||
      safeCli.ssh ||
      "",
    description: getCleanCliDescription(safeCli.description, deviceId)
  };
}

function normalizeCliAccessResponse(result, sessionId = "") {
  const safeResult =
    result && typeof result === "object" && !Array.isArray(result)
      ? result
      : {};
  const cliAccess = Array.isArray(result)
    ? result
    : safeResult.cli_access || safeResult.devices || safeResult.items || [];

  return {
    success: safeResult.success ?? true,
    session_id: safeResult.session_id || sessionId || "",
    mode:
      safeResult.mode ||
      safeResult.cli_mode ||
      safeResult.access_mode ||
      safeResult.current_mode ||
      "browser_cli_mvp",
    browser_cli_available: Boolean(safeResult.browser_cli_available),
    ssh_gateway_available: Boolean(safeResult.ssh_gateway_available),
    cli_access: Array.isArray(cliAccess)
      ? cliAccess.map((cli, index) => normalizeCliAccess(cli, index))
      : [],
    message: safeResult.message || ""
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

export async function listLabSessions({ limit = 50, student_id } = {}) {
  const safeLimit = Math.min(Math.max(Number(limit) || 50, 1), 200);

  if (USE_MOCK_API) {
    await wait();

    const sessions = MOCK_LAB_HISTORY.sessions.slice(0, safeLimit);

    return {
      ...MOCK_LAB_HISTORY,
      sessions,
      count: sessions.length
    };
  }

  const params = new URLSearchParams();
  params.set("limit", String(safeLimit));

  if (student_id) {
    params.set("student_id", student_id);
  }

  return request(`/labs?${params.toString()}`);
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

function getWebSocketBaseUrl() {
  if (API_BASE_URL.startsWith("https://")) {
    return API_BASE_URL.replace(/^https:\/\//, "wss://");
  }

  if (API_BASE_URL.startsWith("http://")) {
    return API_BASE_URL.replace(/^http:\/\//, "ws://");
  }

  if (API_BASE_URL.startsWith("/") && typeof window !== "undefined") {
    const websocketProtocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    return `${websocketProtocol}//${window.location.host}${API_BASE_URL}`;
  }

  return API_BASE_URL;
}

function getMockWebCliReadiness(sessionId, deviceId = "") {
  const devices = MOCK_WEB_CLI_READINESS.devices.map((device) => ({
    ...device
  }));

  const filteredDevices = deviceId
    ? devices.filter((device) => device.device_id === deviceId)
    : devices;

  return {
    ...MOCK_WEB_CLI_READINESS,
    session_id: sessionId,
    devices: filteredDevices.length > 0
      ? filteredDevices
      : [
          {
            device_id: deviceId,
            container_name: "-",
            docker_available: true,
            container_running: false,
            ready: false,
            error_code: "WEB_CLI_DEVICE_NOT_FOUND",
            message: "MOCK: Selected device is not available for this lab session."
          }
        ],
    ready: filteredDevices.length > 0 && filteredDevices.every((device) => device.ready),
    error_code: filteredDevices.length > 0 ? null : "WEB_CLI_DEVICE_NOT_FOUND",
    message: filteredDevices.length > 0
      ? "MOCK: Web CLI readiness check completed."
      : "MOCK: Selected device is not available for this lab session."
  };
}

export async function getWebCliReadiness(sessionId) {
  if (!sessionId) {
    throw new Error("sessionId is required for Web CLI readiness.");
  }

  if (USE_MOCK_API) {
    await wait();
    return getMockWebCliReadiness(sessionId);
  }

  return request(`/labs/${encodeURIComponent(sessionId)}/cli/readiness`);
}

export async function getWebCliDeviceReadiness(sessionId, deviceId) {
  if (!sessionId) {
    throw new Error("sessionId is required for Web CLI readiness.");
  }

  if (!deviceId) {
    throw new Error("deviceId is required for Web CLI readiness.");
  }

  if (USE_MOCK_API) {
    await wait();
    return getMockWebCliReadiness(sessionId, deviceId);
  }

  return request(`/labs/${encodeURIComponent(sessionId)}/cli/readiness/${encodeURIComponent(deviceId)}`);
}

export function getWebCliUrl({ sessionId, deviceId }) {
  if (!sessionId) {
    throw new Error("sessionId is required for Web CLI.");
  }

  if (!deviceId) {
    throw new Error("deviceId is required for Web CLI.");
  }

  const token = getAuthToken();

  if (!token) {
    throw new Error("A login token is required for Web CLI.");
  }

  return `${getWebSocketBaseUrl()}/labs/${encodeURIComponent(sessionId)}/cli/ws/${encodeURIComponent(deviceId)}?token=${encodeURIComponent(token)}`;
}

export async function getDatabaseReadiness() {
  if (USE_MOCK_API) {
    await wait();
    return MOCK_DATABASE_READINESS;
  }

  return request("/meta/database-readiness");
}

export async function getRuntimeReadiness() {
  if (USE_MOCK_API) {
    await wait();
    return MOCK_RUNTIME_READINESS;
  }

  return request("/meta/runtime-readiness");
}

export async function getCliAccessModes() {
  if (USE_MOCK_API) {
    await wait();
    return MOCK_CLI_ACCESS_MODES;
  }

  return request("/meta/cli-access-modes");
}

export async function getCliAccess(sessionId) {
  if (!sessionId) {
    throw new Error("sessionId is required.");
  }

  if (USE_MOCK_API) {
    await wait();

    const session = createMockLabSession({
      student_id: "muhammed",
      difficulty: "hard",
      topology_template: "basic-two-router"
    });

    return normalizeCliAccessResponse(
      {
        success: true,
        session_id: sessionId,
        mode: session.cli_access_mode || "local_docker_exec_demo",
        cli_access: session.cli_access,
        browser_cli_available: false,
        ssh_gateway_available: false,
        message: "MOCK: CLI access metadata loaded."
      },
      sessionId
    );
  }

  try {
    const result = await request(`/labs/${sessionId}/cli`);

    return normalizeCliAccessResponse(result, sessionId);
  } catch (error) {
    if (error.status === 404) {
      const session = await getSession(sessionId);

      return normalizeCliAccessResponse(
        {
          success: true,
          session_id: sessionId,
          mode:
            session.cli_access_mode ||
            session.cli_mode ||
            session.access_mode ||
            "local_docker_exec_demo",
          cli_access: session.cli_access || [],
          browser_cli_available: false,
          ssh_gateway_available: false,
          message: "CLI endpoint was not available. Session CLI access data is being used."
        },
        sessionId
      );
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


export async function finishSession(sessionId) {
  if (!sessionId) {
    throw new Error("sessionId is required.");
  }

  if (USE_MOCK_API) {
    await wait();

    return {
      success: true,
      session_id: sessionId,
      status: "finished",
      message: "MOCK: Lab finished successfully. Validation history is preserved."
    };
  }

  return request(`/labs/${encodeURIComponent(sessionId)}/finish`, {
    method: "POST"
  });
}

function normalizeHintItem(item, index) {
  if (typeof item === "string") {
    return {
      id: `hint-${index + 1}`,
      topic: "General Troubleshooting",
      device: "",
      level: "general",
      message: item
    };
  }

  const safeItem = item && typeof item === "object" ? item : {};

  return {
    id: safeItem.id || safeItem.hint_id || `hint-${index + 1}`,
    topic: safeItem.topic || safeItem.category || "General Troubleshooting",
    device: safeItem.device || safeItem.device_id || safeItem.node || "",
    level: safeItem.level || safeItem.type || "general",
    message:
      safeItem.message ||
      safeItem.hint ||
      safeItem.description ||
      "Review the related configuration area and validate again."
  };
}

function normalizeHintsPayload(payload, sessionId = "") {
  const safePayload = payload && typeof payload === "object" ? payload : {};
  const rawHints = Array.isArray(safePayload.hints)
    ? safePayload.hints
    : Array.isArray(payload)
      ? payload
      : [];

  return {
    success: safePayload.success ?? true,
    session_id: safePayload.session_id || sessionId || "",
    hints: rawHints.map((item, index) => normalizeHintItem(item, index)),
    message: safePayload.message || ""
  };
}

export async function getLabHints(sessionId) {
  if (!sessionId) {
    throw new Error("sessionId is required.");
  }

  if (USE_MOCK_API) {
    await wait();

    return normalizeHintsPayload(
      {
        success: true,
        session_id: sessionId,
        hints: DEFAULT_STUDENT_HINTS,
        message: "MOCK: Student-safe hints loaded."
      },
      sessionId
    );
  }

  const result = await request(`/labs/${encodeURIComponent(sessionId)}/hints`);

  return normalizeHintsPayload(result, sessionId);
}

function sanitizeHistoryCheck(check, index) {
  const normalizedCheck = normalizeValidationCheck(check, index);

  delete normalizedCheck.evidence;
  delete normalizedCheck.observed_state;
  delete normalizedCheck.expected_state;
  delete normalizedCheck.failed_command_output;
  delete normalizedCheck.expected_outputs;
  delete normalizedCheck.validation_command;
  delete normalizedCheck.injection_commands;

  return normalizedCheck;
}

function normalizeValidationAttempt(item, index) {
  const safeItem = item && typeof item === "object" ? item : {};
  const checks = Array.isArray(safeItem.checks)
    ? safeItem.checks.map((check, checkIndex) => sanitizeHistoryCheck(check, checkIndex))
    : [];
  const passedChecks =
    safeItem.passed_checks ??
    checks.filter((check) => check.passed).length;
  const totalChecks = safeItem.total_checks ?? checks.length;
  const failedChecks =
    safeItem.failed_checks ??
    Math.max(totalChecks - passedChecks, 0);

  return {
    attempt_number: safeItem.attempt_number ?? safeItem.attemptNumber ?? index + 1,
    score: safeItem.score ?? null,
    passed: safeItem.passed ?? false,
    passed_checks: passedChecks,
    failed_checks: failedChecks,
    total_checks: totalChecks,
    created_at: safeItem.created_at || safeItem.createdAt || safeItem.timestamp || "",
    checks
  };
}

function normalizeValidationHistoryPayload(payload, sessionId = "") {
  const safePayload = payload && typeof payload === "object" ? payload : {};
  const rawAttempts = Array.isArray(safePayload.attempts)
    ? safePayload.attempts
    : Array.isArray(payload)
      ? payload
      : [];

  return {
    success: safePayload.success ?? true,
    session_id: safePayload.session_id || sessionId || "",
    attempts: rawAttempts.map((item, index) => normalizeValidationAttempt(item, index)),
    message: safePayload.message || ""
  };
}

export async function getValidationHistory(sessionId) {
  if (!sessionId) {
    throw new Error("sessionId is required.");
  }

  if (USE_MOCK_API) {
    await wait();

    return normalizeValidationHistoryPayload(
      {
        success: true,
        session_id: sessionId,
        attempts: [
          {
            attempt_number: 1,
            score: 40,
            passed: false,
            passed_checks: 2,
            failed_checks: 3,
            total_checks: 5,
            created_at: "2026-05-25T02:10:00Z",
            checks: mockValidationResult.checks || []
          },
          {
            attempt_number: 2,
            score: 80,
            passed: false,
            passed_checks: 4,
            failed_checks: 1,
            total_checks: 5,
            created_at: "2026-05-25T02:18:00Z",
            checks: mockValidationResult.checks || []
          }
        ],
        message: "MOCK: Validation history loaded."
      },
      sessionId
    );
  }

  const result = await request(`/labs/${encodeURIComponent(sessionId)}/validation-history`);

  return normalizeValidationHistoryPayload(result, sessionId);
}

export async function getRecommendations(sessionId) {
  if (!sessionId) {
    throw new Error("sessionId is required.");
  }

  if (USE_MOCK_API) {
    await wait();

    return normalizeRecommendationPayload(
      {
        ...mockRecommendation,
        session_id: sessionId || mockRecommendation.session_id
      },
      sessionId
    );
  }

  const result = await request(`/labs/${sessionId}/recommendations`);

  return normalizeRecommendationPayload(result, sessionId);
}

export async function validateSession(sessionId) {
  if (!sessionId) {
    throw new Error("sessionId is required.");
  }

  if (USE_MOCK_API) {
    await wait(600);

    const recommendationPayload = await getRecommendations(sessionId);

    return normalizeValidationResult(
      {
        ...mockValidationResult,
        session_id: sessionId || mockValidationResult.session_id,
        status: "validated"
      },
      recommendationPayload
    );
  }

  const validationResult = await request(`/labs/${sessionId}/validate`, {
    method: "POST"
  });

  let recommendationPayload = null;

  try {
    recommendationPayload = await getRecommendations(sessionId);
  } catch (error) {
    recommendationPayload = normalizeRecommendationPayload(
      {
        success: false,
        session_id: sessionId,
        status: validationResult?.status || "validated",
        score: validationResult?.score ?? null,
        passed: validationResult?.passed ?? null,
        source: "rule_based",
        fallback_used: true,
        recommendations: validationResult?.recommendations || [],
        message:
          "Validation completed, but recommendation endpoint could not be loaded. Please try again."
      },
      sessionId
    );
  }

  return normalizeValidationResult(validationResult, recommendationPayload);
}

function getMockStudentDetail(studentId) {
  const fallbackDetail = MOCK_STUDENT_DETAIL["demo-student"];
  return MOCK_STUDENT_DETAIL[studentId] || {
    ...fallbackDetail,
    summary: {
      ...fallbackDetail.summary,
      student_id: studentId
    },
    sessions: fallbackDetail.sessions.map((session) => ({
      ...session,
      student_id: studentId,
      session_id: session.session_id.replace("demo", studentId || "student")
    })),
    topic_weaknesses: fallbackDetail.topic_weaknesses,
    score_trend: fallbackDetail.score_trend.map((item) => ({
      ...item,
      session_id: item.session_id.replace("demo", studentId || "student")
    }))
  };
}

export async function getInstructorStudents() {
  if (USE_MOCK_API) {
    await wait();
    return MOCK_INSTRUCTOR_STUDENTS;
  }

  return request("/instructor/students");
}

export async function getInstructorStudentSummary(studentId) {
  if (!studentId) {
    throw new Error("studentId is required.");
  }

  if (USE_MOCK_API) {
    await wait();
    return getMockStudentDetail(studentId).summary;
  }

  return request(`/instructor/students/${encodeURIComponent(studentId)}/summary`);
}

export async function getInstructorStudentSessions(studentId, limit = 50) {
  if (!studentId) {
    throw new Error("studentId is required.");
  }

  const safeLimit = Math.min(Math.max(Number(limit) || 50, 1), 200);

  if (USE_MOCK_API) {
    await wait();
    const detail = getMockStudentDetail(studentId);

    return {
      success: true,
      student_id: studentId,
      sessions: detail.sessions.slice(0, safeLimit),
      message: "MOCK: Student sessions loaded."
    };
  }

  return request(`/instructor/students/${encodeURIComponent(studentId)}/sessions?limit=${safeLimit}`);
}

export async function getInstructorStudentTopicWeaknesses(studentId) {
  if (!studentId) {
    throw new Error("studentId is required.");
  }

  if (USE_MOCK_API) {
    await wait();
    const detail = getMockStudentDetail(studentId);

    return {
      success: true,
      student_id: studentId,
      topic_weaknesses: detail.topic_weaknesses,
      message: "MOCK: Student topic weaknesses loaded."
    };
  }

  return request(`/instructor/students/${encodeURIComponent(studentId)}/topic-weaknesses`);
}

export async function getInstructorStudentScoreTrend(studentId, limit = 50) {
  if (!studentId) {
    throw new Error("studentId is required.");
  }

  const safeLimit = Math.min(Math.max(Number(limit) || 50, 1), 200);

  if (USE_MOCK_API) {
    await wait();
    const detail = getMockStudentDetail(studentId);

    return {
      success: true,
      student_id: studentId,
      score_trend: detail.score_trend.slice(0, safeLimit),
      message: "MOCK: Student score trend loaded."
    };
  }

  return request(`/instructor/students/${encodeURIComponent(studentId)}/score-trend?limit=${safeLimit}`);
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
export const finishLab = finishSession;
export const validateLab = validateSession;
