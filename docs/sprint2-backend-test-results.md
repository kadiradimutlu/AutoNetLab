# Sprint 2 Backend Test Results

This document summarizes Sprint 2 Backend & DevOps test results for AutoNetLab.

Bu dokuman AutoNetLab Sprint 2 Backend & DevOps test sonuclarini ozetler.

---

## Environment / Ortam

| Item | Value |
|---|---|
| OS | Windows 11 Pro + WSL2 Ubuntu |
| Backend Runtime | FastAPI + Uvicorn |
| Container Runtime | Docker inside WSL2 |
| Network Lab Runtime | Containerlab |
| Containerlab Version | 0.75.0 |
| Python in WSL | Python 3.12.x |
| Branch | feature/sprint2-backend |

---

## Implemented Sprint 2 Backend Features

1. Containerlab Adapter / Containerlab Adaptoru
   - Real containerlab deploy, inspect and destroy commands.
   - subprocess based safe command execution.
   - return_code, stdout and stderr are captured.

2. Topology Generator / Topoloji Uretici
   - easy, medium and hard template support.
   - Session-specific lab.clab.yml generation.

3. Error Injection v1 / Hata Enjeksiyonu v1
   - Difficulty-based error count.
   - injected_errors.json generation.
   - Device config file generation.

4. Validation Service v1 / Dogrulama Servisi v1
   - Reads injected_errors.json and configs/<device>.conf files.
   - Produces checks, score and recommendations.

5. Session Persistence v1 / Oturum Kaliciligi v1
   - session.json generation.
   - Session reload after backend restart.

---

## Test Results

### Test 1 - Health Check

Command:

curl http://127.0.0.1:8000/api/v1/health

Expected:

status ok and service AutoNetLab Backend API.

Result: Passed.

### Test 2 - Create Lab Session

Expected:

- New session_id is returned.
- Status is created.
- Topology is generated according to difficulty.
- Injected errors are returned.
- Session files are created under containerlab/generated/<session_id>/.

Result: Passed.

### Test 3 - Generated Session Files

Expected files:

- lab.clab.yml
- session.json
- errors/injected_errors.json
- configs/r1.conf
- configs/r2.conf

For hard difficulty, r3.conf and r4.conf can also exist.

Result: Passed.

### Test 4 - Containerlab Deploy

Expected:

status deployed and return_code 0.

Result: Passed.

### Test 5 - Containerlab Inspect

Expected:

status deployed and return_code 0. Output includes running Containerlab nodes.

Result: Passed.

### Test 6 - Containerlab Destroy

Expected:

status destroyed and return_code 0. docker ps shows no running lab containers.

Result: Passed.

### Test 7 - Error Injection v1

Expected:

- Hard difficulty generates 5 injected errors.
- injected_errors.json is created.
- Config files include injected error markers.

Observed example error codes:

- IP_ADDRESS_MISMATCH
- VLAN_MISMATCH
- WRONG_GATEWAY
- MISSING_ROUTE
- ACL_DENY_ANY

Result: Passed.

### Test 8 - Validation Service v1

Initial expected result:

passed false and score 0.

After manually removing one error marker from config file:

score increased to 20 and one check became true.

Result: Passed.

### Test 9 - Session Persistence v1

Scenario:

A session was created, deployed, destroyed, backend was restarted, and the same session was requested again.

Expected:

GET /labs/<session_id> returns the same session from session.json.

Observed:

- Same session_id.
- difficulty medium.
- status destroyed.
- nodes r1, r2, r3.
- errors 3.

Result: Passed.

---

## Notes / Notlar

- containerlab/generated/ is intentionally ignored by Git.
- backend/.venv-wsl/ is intentionally ignored by Git.
- When running Containerlab from /mnt/c/..., this warning can appear: unable to adjust Labdir file ACLs: operation not supported.
- This warning did not block deploy, inspect or destroy during MVP testing.

---

## Sprint 2 Backend Status

Sprint 2 Backend & DevOps MVP is functional.

Completed modules:

- Containerlab Adapter
- Topology Generator
- Error Injection v1
- Validation Service v1
- Session Persistence v1
- Updated API contract
