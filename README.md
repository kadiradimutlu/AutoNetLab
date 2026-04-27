# AutoNetLab

AutoNetLab is an intelligent automated network training laboratory.

The system generates virtual network labs using Containerlab and YAML-based topology definitions, injects configuration errors based on selected difficulty levels, validates student solutions using Python-based scripts, and returns structured JSON results to a web dashboard.

## Core Modules

- Backend API / Orchestrator
- Topology Generator
- Containerlab Runtime Adapter
- Error Injection Engine
- Validation & Scoring Engine
- Web Dashboard
- Session & Results Storage

## Branch Strategy

- main: stable version
- dev: development integration branch
- feature/backend-api: backend API development
- feature/containerlab: Containerlab experiments
- feature/topology-generator: topology generation module
- feature/error-injection: error injection module
- feature/frontend-dashboard: frontend dashboard development