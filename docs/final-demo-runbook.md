# Final Demo Runbook

This runbook defines the recommended final presentation flow for AutoNetLab.

## Final demo goal

The preferred presentation flow is:

```text
Open laptop browser -> enter public VM URL -> use AutoNetLab without installing anything locally

The cloud VM/server should host:

React frontend
FastAPI backend
Docker runtime
Containerlab runtime
Web CLI bridge
Primary and backup environments

Primary:

Free cloud VM/server
Ubuntu Linux
Docker + Containerlab installed
AutoNetLab backend and frontend running on the VM

Backup:

Local laptop WSL2 environment
Docker Desktop + WSL2 integration
Containerlab inside WSL
Local docker exec fallback commands
Pre-demo checklist

Before the presentation:

Pull latest dev branch.
Run backend tests.
Run frontend build.
Verify Docker.
Verify Containerlab.
Verify runtime readiness endpoint.
Verify frontend URL.
Verify backend health endpoint.
Verify Web CLI readiness endpoint.
Prepare backup local environment.
VM commands

Run inside the VM:

git checkout dev
git pull origin dev
python -m pytest
cd frontend
npm run build
cd ..
docker ps
docker info
containerlab version
Start backend on VM
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
Start frontend on VM

Development/demo mode:

cd frontend
npm run dev -- --host 0.0.0.0

Production-like mode will be improved in Sprint 15 with Nginx or a similar static serving/proxy setup.

Runtime readiness

After backend starts:

GET /api/v1/meta/runtime-readiness

Expected:

ready: true
docker_available: true
docker_ps_ok: true
containerlab_available: true
templates_dir_exists: true
Demo flow
Open the public VM URL in the presentation laptop browser.
Show Login page.
Login as student.
Create a lab.
Show topology visualization.
Deploy lab.
Open CLI Access / Web CLI panel.
Check readiness.
Connect Web CLI if ready.
Run a simple command in the terminal.
Validate lab.
Show validation result and recommendations.
Logout or switch role.
Login as instructor.
Show Instructor Dashboard v2.
Select a student.
Show student summary, session history, topic weaknesses, and score trend.
If Web CLI runtime fails
Show readiness error clearly.
Use local docker exec fallback command.
Continue demo with validation, recommendation, and instructor dashboard flow.
If cloud VM fails
Switch to local laptop WSL2 backup.
Start backend locally.
Start frontend locally.
Use localhost or local network address.
Keep the demo moving; do not debug cloud infrastructure live during presentation.
Do not do during demo
Do not merge branches.
Do not run risky dependency upgrades.
Do not reset generated runtime files unless needed.
Do not switch to main unless presenting a stable release intentionally.
Do not expose the demo VM publicly for longer than necessary.
