import mockDifficulties from "../data/mock_difficulties.json";
import mockLabSession from "../data/mock_lab_session.json";
import mockValidationResult from "../data/mock_validation_result_backend.json";

const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API !== "false";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

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
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json"
    },
    ...options
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json();
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
    message: "Lab session created successfully."
  };
}

export async function getDifficulties() {
  if (USE_MOCK_API) {
    await wait();
    return mockDifficulties;
  }

  return request("/meta/difficulties");
}

export async function createLab({
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

export async function getLab(sessionId) {
  if (USE_MOCK_API) {
    await wait();

    return {
      ...mockLabSession,
      session_id: sessionId || mockLabSession.session_id
    };
  }

  return request(`/labs/${sessionId}`);
}

export async function deployLab(sessionId) {
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

export async function destroyLab(sessionId) {
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

export async function validateLab(sessionId) {
  if (USE_MOCK_API) {
    await wait(600);

    return {
      ...mockValidationResult,
      session_id: sessionId || mockValidationResult.session_id,
      status: "validated"
    };
  }

  return request(`/labs/${sessionId}/validate`, {
    method: "POST"
  });
}