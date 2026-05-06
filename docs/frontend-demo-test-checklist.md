# AutoNetLab Frontend Demo Test Checklist

This checklist was prepared for Sprint 4 frontend polishing, manual end-to-end testing, and final project demonstration.

## Environment

| Item | Value |
|---|---|
| Operating System | Windows 11 |
| Frontend Framework | React + Vite |
| Backend Framework | FastAPI |
| API Base URL | http://127.0.0.1:8000/api/v1 |
| Frontend URL | http://localhost:5173 |
| Test Type | Manual end-to-end test |

## Pre-Test Requirements

| Step | Command / Action | Expected Result | Status |
|---|---|---|---|
| 1 | Start FastAPI backend | Backend runs on http://127.0.0.1:8000 | Pending |
| 2 | Start React frontend with `npm run dev` | Frontend runs on http://localhost:5173 | Pending |
| 3 | Check backend health endpoint | `/api/v1/health` returns status ok | Pending |
| 4 | Check frontend build with `npm run build` | Production build completes successfully | Pending |
| 5 | Check frontend lint with `npm run lint` | No lint errors | Pending |

## End-to-End Test Cases

| Test ID | Test Name | Steps | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| FE-01 | Home Page Load | Open the frontend application in the browser. | Home page loads without blank screen or console error. |  | Pending |
| FE-02 | Create Lab Page | Navigate to Create Lab page. | Difficulty selection and lab creation form are visible. |  | Pending |
| FE-03 | Create Easy Lab | Select Easy difficulty and create a lab. | A new lab session is created and user is navigated to session details. |  | Pending |
| FE-04 | Session Detail View | Review the session detail page. | Session ID, student, difficulty, status, injected errors, and topology are displayed. |  | Pending |
| FE-05 | Topology Overview | Check the topology card. | Nodes and links are displayed clearly. |  | Pending |
| FE-06 | CLI Access View | Check the CLI access section. | Device name, container name, access method, command, and copy button are visible. |  | Pending |
| FE-07 | Copy CLI Command | Click the Copy button next to a CLI command. | Command is copied and a success message is displayed. |  | Pending |
| FE-08 | Deploy Lab | Click Deploy Lab. | Deployment result or clear error message is displayed. |  | Pending |
| FE-09 | Validation Page Navigation | Click Validate Lab. | User is navigated to the Validation Result page. |  | Pending |
| FE-10 | Run Validation | Click Run Validation. | Score, passed checks, failed checks, and recommendations are displayed. |  | Pending |
| FE-11 | Recommendation Cards | Review recommendation section. | Topic, priority, related error type, and message are readable. |  | Pending |
| FE-12 | Destroy Lab | Click Destroy Lab if available. | Destroy result or clear error message is displayed. |  | Pending |
| FE-13 | Backend Down Error Handling | Stop the backend and try an API-based action. | Frontend shows a clear backend unreachable error instead of blank screen. |  | Pending |
| FE-14 | Invalid Session Handling | Try to access or validate an invalid session ID if possible. | Frontend shows a clear invalid session or endpoint error. |  | Pending |

## Browser Debug Checklist

During testing, the following browser tools should be checked:

| Area | What to Check | Expected Result |
|---|---|---|
| Console | JavaScript errors | No unexpected runtime errors |
| Network | API request URLs | Requests should go to the correct backend base URL |
| Network | HTTP status codes | 200 for successful requests, clear UI message for errors |
| UI | Empty or undefined values | No visible `undefined`, `null`, or `[object Object]` text |
| UI | Language consistency | Demo UI should remain English-only for now |

## Notes

- The frontend uses centralized API error handling.
- Backend, CORS, 404, 422, and 500 errors are displayed with user-friendly messages.
- CLI commands are shown in readable command boxes with copy buttons.
- Validation results show score, check metrics, failed checks, and recommendations.
- This checklist can be used as evidence for the final report testing section.
