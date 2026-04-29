# AutoNetLab Frontend Dashboard Demo Checklist

This document explains how to run and test the current AutoNetLab frontend dashboard demo.

## Current Branch

Frontend dashboard work is developed on:

```text
feature/dashboard
```

## How to Run the Dashboard

From the project root:

```powershell
cd frontend
npm install
npm run dev
```

Then open:

```text
http://localhost:5173/
```

## How to Build the Dashboard

From the `frontend` folder:

```powershell
npm run build
```

Expected result:

```text
✓ built successfully
```

## How to Run Lint Check

From the `frontend` folder:

```powershell
npm run lint
```

Expected result:

```text
No ESLint errors
```

## Pages Included

The dashboard currently includes these pages:

| Page | Purpose |
|---|---|
| Home | Shows current session summary and quick navigation. |
| Create Lab | Allows selecting difficulty and creating a mock lab session. |
| Session Detail | Shows session information and topology details. |
| Validation Result | Shows validation result, score, PASS/FAIL checks, and recommendations. |

## Mock Data Files

Mock JSON files are located in:

```text
frontend/src/data
```

Current mock files:

```text
mock_session.json
mock_topology.json
mock_validation_result.json
mock_recommendation.json
```

## API Service Layer

Frontend API logic is located in:

```text
frontend/src/services/apiService.js
```

The dashboard currently uses mock JSON data by default.

Mock/real API switch is controlled by:

```env
VITE_USE_MOCK_API=true
```

When the backend API is ready, this can be changed to:

```env
VITE_USE_MOCK_API=false
```

## Demo Flow

Recommended demo order:

1. Open the Home page.
2. Show the current session summary.
3. Go to Create Lab.
4. Select Easy, Medium, and Hard difficulty values.
5. Create a new session.
6. Show Session Detail page.
7. Show topology devices and links.
8. Go to Validation Result page.
9. Click Run Validation.
10. Show score, PASS/FAIL checks, and recommendations.

## Current Status

Completed:

- React + Vite frontend setup
- Simple CSS-based dashboard UI
- Mock JSON data
- API service layer
- Mock API / real API switch
- Loading, empty, and error states
- Validation result UI
- Build check
- Lint check

Pending future integration:

- Real backend API connection
- Real Containerlab topology data
- Real validation engine output
- Real recommendation module output