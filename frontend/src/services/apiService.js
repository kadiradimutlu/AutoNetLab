import mockSession from "../data/mock_session.json";
import mockTopology from "../data/mock_topology.json";
import mockValidationResult from "../data/mock_validation_result.json";
import mockRecommendation from "../data/mock_recommendation.json";

const USE_MOCK_API = import.meta.env.VITE_USE_MOCK_API !== "false";
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

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

export async function createSession(difficulty) {
  if (USE_MOCK_API) {
    await wait();

    return {
      ...mockSession,
      sessionId: `sess-${Date.now()}`,
      difficulty,
      status: "Created",
      progress: 0,
      createdAt: new Date().toISOString()
    };
  }

  return request("/sessions", {
    method: "POST",
    body: JSON.stringify({ difficulty })
  });
}

export async function getSession(sessionId) {
  if (USE_MOCK_API) {
    await wait();

    return {
      ...mockSession,
      sessionId
    };
  }

  return request(`/sessions/${sessionId}`);
}

export async function getTopology(topologyId) {
  if (USE_MOCK_API) {
    await wait();

    return {
      ...mockTopology,
      topologyId
    };
  }

  return request(`/topologies/${topologyId}`);
}

export async function validateSession(sessionId) {
  if (USE_MOCK_API) {
    await wait(600);

    return {
      ...mockValidationResult,
      sessionId,
      checkedAt: new Date().toISOString()
    };
  }

  return request(`/sessions/${sessionId}/validate`, {
    method: "POST"
  });
}

export async function getRecommendation(sessionId) {
  if (USE_MOCK_API) {
    await wait();

    return {
      ...mockRecommendation,
      sessionId
    };
  }

  return request(`/sessions/${sessionId}/recommendations`);
}