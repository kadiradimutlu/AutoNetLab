# Web CLI Runtime Notes

This document summarizes Sprint 12 Web CLI runtime behavior.

## Current mode

- Primary mode: browser_cli_mvp
- Fallback mode: local_docker_exec_demo_fallback

## Runtime readiness

The backend now exposes readiness endpoints before opening Web CLI:

- GET /api/v1/labs/{session_id}/cli/readiness
- GET /api/v1/labs/{session_id}/cli/readiness/{device_id}

These endpoints check:

- whether the lab is deployed
- whether Docker is available
- whether the expected device container is running
- whether the selected device is part of the lab session

## Web CLI limitations

Sprint 12 still keeps Web CLI as an MVP-level browser terminal bridge.

Known limitations:

- Full PTY/TTY behavior is not production-grade yet.
- Terminal resizing is not fully handled yet.
- Disconnect/reconnect UX can be improved further.
- Runtime success depends on Docker and Containerlab being healthy in the backend environment.

## Demo recommendation

For the final demo, use two paths:

- Primary: VM or Ubuntu environment where Docker and Containerlab are installed correctly.
- Backup: local laptop WSL2 environment with local docker exec fallback commands available.

## Safety rule

The browser must never send container_name directly. Backend resolves container_name from trusted session metadata.
