# Sprint 1 Test Results

This document summarizes the backend API and Containerlab manual test results for Sprint 1.

Bu doküman, Sprint 1 kapsamında yapılan backend API ve Containerlab manuel test sonuçlarını özetler.

---

## 1. Backend API Test Summary

Backend framework:

```text
FastAPI
```

Backend base URL:

```text
http://127.0.0.1:8000/api/v1
```

Swagger/OpenAPI URL:

```text
http://127.0.0.1:8000/docs
```

---

## 2. Tested API Endpoints

| Endpoint | Method | Result | Description |
|---|---|---|---|
| `/api/v1/health` | GET | PASS | Backend health check returned status ok. |
| `/api/v1/meta/difficulties` | GET | PASS | Difficulty levels easy, medium, hard returned successfully. |
| `/api/v1/labs` | POST | PASS | New lab session created successfully. |
| `/api/v1/labs/{session_id}` | GET | PASS | Created lab session retrieved successfully. |
| `/api/v1/labs/{session_id}/deploy` | POST | PASS | Mock deploy response returned successfully. |
| `/api/v1/labs/{session_id}/validate` | POST | PASS | Mock validation result returned with score and recommendations. |
| `/api/v1/labs/{session_id}/destroy` | POST | PASS | Mock destroy response returned successfully. |

---

## 3. Example Lab Session ID

```text
lab-775caeb5
```

---

## 4. Backend Test Flow

The following API flow was tested successfully:

```text
create → get → deploy → validate → destroy → get
```

Final session status after destroy:

```json
{
  "status": "destroyed"
}
```

---

## 5. Containerlab Environment Test

Environment:

```text
Windows 11 Pro + WSL2 Ubuntu
```

Containerlab version:

```text
0.75.0
```

Docker test command:

```bash
docker run hello-world
```

Result:

```text
PASS
```

Docker returned:

```text
Hello from Docker!
```

---

## 6. Containerlab Topology Test

Topology file:

```text
containerlab/topologies/sprint1-basic.clab.yml
```

Topology name:

```text
autonetlab-sprint1
```

Nodes:

```text
r1
r2
```

Image:

```text
alpine:latest
```

Manual deploy command:

```bash
containerlab deploy -t containerlab/topologies/sprint1-basic.clab.yml
```

Result:

```text
PASS
```

Created containers:

```text
clab-autonetlab-sprint1-r1
clab-autonetlab-sprint1-r2
```

Manual container access command:

```bash
docker exec -it clab-autonetlab-sprint1-r1 sh
```

Inside the container, interface check command:

```bash
ip addr
```

Result:

```text
PASS
```

Interfaces such as `eth0` and `eth1` were visible.

Manual destroy command:

```bash
containerlab destroy -t containerlab/topologies/sprint1-basic.clab.yml
```

Result:

```text
PASS
```

After destroy, `docker ps` showed no running AutoNetLab containers.

---

## 7. Sprint 1 Result

Sprint 1 backend and Containerlab manual environment tests were completed successfully.

Current status:

```text
Backend API MVP is working.
Swagger/OpenAPI documentation is available.
Frontend mock JSON format is ready.
Docker and Containerlab are working inside WSL2 Ubuntu.
First manual Containerlab deploy/destroy test is successful.
```