# Sprint 8 CLI Access Decision / CLI Erişim Modeli Kararı

This document explains the Sprint 8 CLI access / CLI erişimi decision.

## Decision

Sprint 8 keeps the existing docker exec local demo mode / yerel demo modu as the stable default CLI access model.

Current mode:

```text
local_docker_exec_demo
```

Planned or future modes:

```text
ssh_gateway_planned
browser_cli_future_work
```

## Why docker exec local demo mode remains default

The current backend already provides stable CLI access information for each Containerlab node:

```text
docker exec -it <container_name> sh
```

This is suitable for local demo and academic prototype usage because:

- It is simple.
- It is easy to explain during demo.
- It avoids terminal streaming complexity.
- It does not require credential management.
- It does not add SSH gateway security risks.
- It keeps validation and scenario quality as the Sprint 8 priority.

## SSH Gateway / SSH geçidi

SSH Gateway is planned but not enabled in Sprint 8.

Reasons:

- Needs user/session isolation.
- Needs credential handling.
- Needs secure gateway hardening.
- Needs authorization rules.
- Needs more integration testing.

Status:

```text
ssh_gateway_planned
```

## Browser-based CLI / Tarayıcı tabanlı CLI

Browser-based CLI is future work.

Reasons:

- Requires WebSocket or streaming terminal support.
- Requires session authorization and isolation.
- Requires safe command execution boundaries.
- Adds frontend and backend complexity.
- Can destabilize the current working demo flow.

Status:

```text
browser_cli_future_work
```

## API metadata

Sprint 8 exposes CLI mode metadata through:

```text
GET /api/v1/meta/cli-access-modes
```

The lab CLI endpoint also returns mode information:

```text
GET /api/v1/labs/{session_id}/cli
```

Expected current mode:

```text
local_docker_exec_demo
```

## Final note

Sprint 8 prioritizes stable validation checks / doğrulama kontrolleri, better hard scenarios / daha iyi zor senaryolar, and reliable demo behavior.

SSH Gateway and Browser-based CLI should be developed later in a separate experimental branch if enough time remains.
