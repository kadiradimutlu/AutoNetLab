# AutoNetLab

AutoNetLab is an intelligent automated network training laboratory developed as a Computer Engineering graduation project.

The system creates Containerlab-based virtual network topologies, injects configuration errors according to the selected difficulty level, allows students to troubleshoot devices through CLI access, validates the result, calculates a score, and provides learning recommendations.

## Project Overview

Traditional network laboratories are often static, manual, and difficult to evaluate objectively. AutoNetLab aims to provide a lightweight, repeatable, and automated training environment for network troubleshooting education.

Main capabilities:

- Create lab sessions with Easy, Medium, or Hard difficulty
- Generate Containerlab topology files from templates
- Inject configuration errors automatically
- Provide CLI access commands for each network device
- Deploy, inspect, and destroy Containerlab topologies
- Validate student fixes
- Produce score and recommendations
- Display the process through a React dashboard

## Technologies Used

### Backend

- Python
- FastAPI
- Uvicorn
- Pydantic
- SQLite / session metadata files
- Pytest

### Network Runtime

- Docker
- WSL2 / Ubuntu
- Containerlab
- YAML topology files

### Frontend

- React
- Vite
- JavaScript
- REST API integration

## Requirements

Recommended environment:

- Windows 11 Pro
- WSL2 Ubuntu
- Docker Desktop with WSL2 integration enabled
- Containerlab installed inside WSL/Ubuntu
- Python virtual environment for backend
- Node.js and npm for frontend

## Project Structure

```text
AutoNetLab/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── schemas/
│   │   └── services/
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
├── containerlab/
│   ├── templates/
│   └── generated/
├── frontend/
└── docs/