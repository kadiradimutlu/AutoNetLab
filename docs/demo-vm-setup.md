# Free Cloud VM Demo Setup Guide

This guide describes the recommended primary demo environment for AutoNetLab.

## Goal

The final demo should work like this:

- The project runs on a free cloud VM/server.
- Backend, frontend, Docker, Containerlab, and Web CLI run on the VM.
- The presentation laptop only opens a browser.
- The instructor/jury can access AutoNetLab from a browser without installing anything locally.

## Primary demo environment

Recommended primary target:

- Free cloud VM with Ubuntu Linux
- Docker installed and running
- Containerlab installed
- Git installed
- Python virtual environment for backend
- Node.js and npm for frontend
- Public IP or public DNS address for browser access

Candidate provider:

- Oracle Cloud Always Free VM will be evaluated first in Sprint 14.
- If Oracle Cloud is not available or quota is not granted, use another free/trial VM option or fall back to local WSL2.

## Backup demo environment

Backup target:

- Local laptop WSL2 Ubuntu environment
- Docker Desktop + WSL2 integration
- Containerlab installed in WSL
- Local docker exec fallback commands available

## Why cloud VM is preferred

AutoNetLab uses Docker and Containerlab for runtime lab orchestration. A Linux VM/server gives a more predictable runtime environment than relying only on Windows + Docker Desktop + WSL during presentation.

The cloud VM also allows this demo flow:

```text
Presentation laptop browser -> public VM address -> AutoNetLab

No local setup is needed for the viewer.

Required runtime tools

Check these inside the VM:

docker --version
docker ps
docker info
containerlab version
git --version
python --version
node --version
npm --version
Backend setup
git clone <repository-url>
cd AutoNetLab/backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
python -m pytest

Run backend:

cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
Frontend setup
cd frontend
npm install
npm run build
npm run dev -- --host 0.0.0.0
Runtime readiness check

After backend starts, open:

http://<VM_PUBLIC_IP>:8000/api/v1/meta/runtime-readiness

Expected important values:

docker_available: true
docker_ps_ok: true
containerlab_available: true
templates_dir_exists: true
ready: true
Demo access goal

Sprint 14 and Sprint 15 will improve this into a cleaner public browser flow:

http://<VM_PUBLIC_IP>

Frontend, backend API, and WebSocket traffic should work from the same VM address.

Backup plan

If cloud VM fails during presentation:

Use the local laptop WSL2 backup environment.
Start backend and frontend locally.
Use Web CLI if available.
If Web CLI runtime has issues, use local docker exec fallback commands.
Continue with validation, recommendation, and instructor dashboard demo flow.
