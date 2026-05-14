# Runtime Preflight Checklist

Use this checklist before running the AutoNetLab demo.

## Target environment

Primary target:

- Free cloud VM/server
- Ubuntu Linux
- Docker + Containerlab installed
- Backend and frontend running on VM
- Presentation laptop accesses AutoNetLab from browser

Backup target:

- Local laptop WSL2 environment
- Docker Desktop + WSL2 integration
- Local docker exec fallback available

## Git state

```bash
git checkout dev
git pull origin dev
git status

Expected:

working tree clean
branch up to date with origin/dev
Backend test
python -m pytest

Expected:

all tests passed
Frontend build
cd frontend
npm run build
cd ..

Expected:

Vite build successful
Docker
docker --version
docker ps
docker info

Expected:

Docker command available
Docker daemon reachable
no permission error
Containerlab
containerlab version

Expected:

Containerlab version printed successfully
Backend health

After backend starts:

GET /api/v1/health

Expected:

status: ok
service: AutoNetLab Backend API
Runtime readiness endpoint

After backend starts:

GET /api/v1/meta/runtime-readiness

Expected important fields:

ready: true
docker_available: true
docker_ps_ok: true
containerlab_available: true
templates_dir_exists: true
Web CLI readiness

After creating and deploying a lab:

GET /api/v1/labs/{session_id}/cli/readiness/{device_id}

Expected:

lab_deployed: true
ready: true
container_running: true
Public access checks

From the presentation laptop browser:

Frontend URL opens.
Login page opens.
Student login works.
Instructor login works.
API requests reach backend.
WebSocket URL works or shows readable readiness/runtime error.
Recovery checklist

If demo runtime fails:

Check Docker daemon.
Run docker ps.
Run docker info.
Run containerlab version.
Run containerlab inspect if a lab was deployed.
Destroy and redeploy lab if needed.
Use local docker exec fallback command.
Continue with validation, recommendation, and instructor dashboard screens.
Backup local WSL2 checklist

On the backup laptop:

wsl docker --version
wsl docker ps
wsl containerlab version

Expected:

Docker works in WSL.
Containerlab works in WSL.
Backend and frontend can run locally.
