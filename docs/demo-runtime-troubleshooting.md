# Demo Runtime Troubleshooting

This document lists common runtime issues for AutoNetLab Web CLI and Containerlab demo flows.

## Check Docker

Run inside the backend runtime environment:

- docker --version
- docker ps
- docker info

On Windows + WSL2, PowerShell can call:

- wsl docker --version
- wsl docker ps

## Check Containerlab

- containerlab version

On Windows + WSL2:

- wsl containerlab version

## Common Web CLI errors

### LAB_NOT_DEPLOYED_FOR_WEB_CLI

Meaning: Lab is created but not deployed.

Action:

- Click Deploy Lab first.
- Then retry Web CLI readiness.

### WEB_CLI_CONTAINER_NOT_RUNNING

Meaning: Session says deployed, but expected Docker container is not running.

Action:

- Run docker ps.
- Run containerlab inspect.
- Destroy and redeploy the lab if needed.

### DOCKER_NOT_FOUND_FOR_WEB_CLI

Meaning: Backend runtime cannot find docker command.

Action:

- Run backend inside WSL/Ubuntu or VM where Docker is installed.
- Verify Docker Desktop WSL integration if using Windows.

### DOCKER_PERMISSION_DENIED_FOR_WEB_CLI

Meaning: Backend runtime cannot access Docker.

Action:

- Check Docker permissions.
- Restart Docker Desktop or WSL session.

## Known local limitation

Docker Desktop + WSL may sometimes create Containerlab bridge/network behavior that differs from a clean Ubuntu VM.

For the final presentation, use:

- primary VM demo environment
- local laptop WSL2 backup environment
- local docker exec fallback commands as recovery path
