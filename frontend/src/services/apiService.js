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
      const message =
        data?.detail ||
        data?.message ||
        `API request failed with status ${response.status}`;

      const error = new Error(message);
      error.status = response.status;
      error.data = data;
      throw error;
    }

    return data;
  } catch (error) {
    if (error instanceof TypeError) {
      const apiError = new Error(
        `Backend API is not reachable. Please check if FastAPI is running at ${API_BASE_URL}.`
      );
      apiError.status = 0;
      throw apiError;
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
        access_method: "docker_exec",
        command: "docker exec -it clab-autonetlab-mock-r1 sh",
        description: "Open CLI access for router r1."
      },
      {
        device_name: "r2",
        container_name: "clab-autonetlab-mock-r2",
        access_method: "docker_exec",
        command: "docker exec -it clab-autonetlab-mock-r2 sh",
        description: "Open CLI access for router r2."
      }
    ],
    message: "Lab session created successfully."
  };
}

function normalizeValidationResult(result) {
  const checks = Array.isArray(result?.checks) ? result.checks : [];
  const passedChecks = checks.filter((check) => check.passed).length;
  const totalChecks = checks.length;

  return {
    ...result,
    passed: Boolean(result?.passed),
    score: result?.score ?? 0,
    checks,
    passed_checks: result?.passed_checks ?? passedChecks,
    total_checks: result?.total_checks ?? totalChecks,
    recommendations: result?.recommendations || result?.recommendation || []
  };
}

function normalizeCliAccess(cli, index) {
  return {
    device_name:
      cli.device_name ||
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

// Backward-compatible aliases.
// Sprint 1 components may still use the old function names.
export const createLab = createSession;
export const getLab = getSession;
export const deployLab = deploySession;
export const destroyLab = destroySession;
export const validateLab = validateSession;