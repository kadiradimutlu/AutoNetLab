# AutoNetLab Dashboard API Contract

This document defines the initial REST/HTTP JSON API contract between the AutoNetLab frontend dashboard and the backend API.

The frontend currently works with mock JSON data. When the backend API is ready, the same response structures can be returned by the backend.

## Base URL

```text
http://localhost:8000/api
```

Frontend environment variable:

```env
VITE_API_BASE_URL=http://localhost:8000/api
```

## Mock / Real API Switch

The frontend uses this environment variable:

```env
VITE_USE_MOCK_API=true
```

- `true`: frontend uses local mock JSON files.
- `false`: frontend sends HTTP requests to the backend API.

---

## 1. Create Lab Session

### Endpoint

```http
POST /sessions
```

### Request Body

```json
{
  "difficulty": "Easy"
}
```

Allowed difficulty values:

```text
Easy
Medium
Hard
```

### Response Body

```json
{
  "sessionId": "sess-001",
  "user": {
    "id": "user-001",
    "name": "Muhammed YILDIZ"
  },
  "labTitle": "Basic VLAN Troubleshooting Lab",
  "difficulty": "Easy",
  "status": "Created",
  "createdAt": "2026-04-29T10:00:00Z",
  "topologyId": "topo-basic-01",
  "progress": 0,
  "score": null
}
```

---

## 2. Get Lab Session

### Endpoint

```http
GET /sessions/{sessionId}
```

### Example

```http
GET /sessions/sess-001
```

### Response Body

```json
{
  "sessionId": "sess-001",
  "user": {
    "id": "user-001",
    "name": "Muhammed YILDIZ"
  },
  "labTitle": "Basic VLAN Troubleshooting Lab",
  "difficulty": "Easy",
  "status": "In Progress",
  "createdAt": "2026-04-29T10:00:00Z",
  "topologyId": "topo-basic-01",
  "progress": 45,
  "score": null
}
```

---

## 3. Get Topology

### Endpoint

```http
GET /topologies/{topologyId}
```

### Example

```http
GET /topologies/topo-basic-01
```

### Response Body

```json
{
  "topologyId": "topo-basic-01",
  "name": "Two Switch VLAN Topology",
  "description": "A simple topology used to practice VLAN configuration and basic connectivity troubleshooting.",
  "devices": [
    {
      "id": "sw1",
      "name": "Switch-1",
      "type": "Switch",
      "managementIp": "192.168.10.2"
    },
    {
      "id": "sw2",
      "name": "Switch-2",
      "type": "Switch",
      "managementIp": "192.168.10.3"
    }
  ],
  "links": [
    {
      "source": "sw1",
      "target": "sw2",
      "interface": "eth2"
    }
  ],
  "expectedGoal": "PC1 and PC2 should communicate through the correct VLAN configuration."
}
```

---

## 4. Validate Session

### Endpoint

```http
POST /sessions/{sessionId}/validate
```

### Example

```http
POST /sessions/sess-001/validate
```

### Response Body

```json
{
  "sessionId": "sess-001",
  "status": "FAIL",
  "score": 65,
  "totalChecks": 4,
  "passedChecks": 2,
  "failedChecks": 2,
  "checkedAt": "2026-04-29T10:20:00Z",
  "summary": "The topology is partially fixed. VLAN assignment is correct on one switch, but trunk configuration and end-to-end connectivity still need attention.",
  "results": [
    {
      "checkId": "check-001",
      "title": "VLAN 10 exists on Switch-1",
      "status": "PASS",
      "message": "VLAN 10 is configured correctly on Switch-1.",
      "relatedTopic": "VLAN"
    },
    {
      "checkId": "check-002",
      "title": "Trunk link allows VLAN 10",
      "status": "FAIL",
      "message": "The trunk link between Switch-1 and Switch-2 does not allow VLAN 10.",
      "relatedTopic": "Trunk Configuration"
    }
  ]
}
```

---

## 5. Get Recommendations

### Endpoint

```http
GET /sessions/{sessionId}/recommendations
```

### Example

```http
GET /sessions/sess-001/recommendations
```

### Response Body

```json
{
  "sessionId": "sess-001",
  "recommendations": [
    {
      "id": "rec-001",
      "topic": "VLAN Trunking",
      "priority": "High",
      "message": "Review how trunk ports carry VLAN traffic between switches."
    },
    {
      "id": "rec-002",
      "topic": "End-to-End Connectivity",
      "priority": "Medium",
      "message": "Practice using ping and interface status commands to verify connectivity."
    }
  ]
}
```

---

## Related Frontend Service Functions

The frontend uses these functions in:

```text
frontend/src/services/apiService.js
```

| Function | Backend Endpoint |
|---|---|
| `createSession(difficulty)` | `POST /sessions` |
| `getSession(sessionId)` | `GET /sessions/{sessionId}` |
| `getTopology(topologyId)` | `GET /topologies/{topologyId}` |
| `validateSession(sessionId)` | `POST /sessions/{sessionId}/validate` |
| `getRecommendation(sessionId)` | `GET /sessions/{sessionId}/recommendations` |

---

## Notes for Backend Integration

The backend should return JSON responses using the same field names used by the frontend mock files.

Important field names:

```text
sessionId
topologyId
difficulty
status
progress
score
devices
links
results
recommendations
```

Keeping these field names stable will allow the frontend to switch from mock data to real backend API with minimal code changes.