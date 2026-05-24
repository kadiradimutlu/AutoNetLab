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

| Step | Command / Action | Expected Result | Actual Result | Status |
|---|---|---|---|---|
| 1 | Start FastAPI backend | Backend runs on http://127.0.0.1:8000 | Backend started successfully. | Passed |
| 2 | Start React frontend with `npm run dev` | Frontend runs on http://localhost:5173 | Frontend started successfully. | Passed |
| 3 | Check backend health endpoint | `/api/v1/health` returns status ok | Health endpoint returned `ok` and `AutoNetLab Backend API`. | Passed |
| 4 | Check frontend build with `npm run build` | Production build completes successfully | Build completed successfully with Vite. | Passed |
| 5 | Check frontend lint with `npm run lint` | No lint errors | ESLint completed without errors. | Passed |
| 6 | Run backend tests with `python -m pytest tests` | Backend API tests pass | 7 backend tests passed, 1 non-blocking warning was shown. | Passed |

## End-to-End Test Cases

| Test ID | Test Name | Steps | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|
| FE-01 | Home Page Load | Open the frontend application in the browser. | Home page loads without blank screen or console error. | Home page loaded successfully. | Passed |
| FE-02 | Create Lab Page | Navigate to Create Lab page. | Difficulty selection and lab creation form are visible. | Create Lab page loaded successfully. | Passed |
| FE-03 | Create Easy Lab | Select Easy difficulty and create a lab. | A new lab session is created and user is navigated to session details. | Easy lab was created successfully. | Passed |
| FE-04 | Session Detail View | Review the session detail page. | Session ID, student, difficulty, status, injected errors, and topology are displayed. | Session Detail page displayed the expected session information. | Passed |
| FE-05 | Topology Overview | Check the topology card. | Nodes and links are displayed clearly. | Topology overview was displayed successfully. | Passed |
| FE-06 | CLI Access View | Check the CLI access section. | Device name, container name, access method, command, and copy button are visible. | CLI access cards were displayed successfully with English descriptions. | Passed |
| FE-07 | Copy CLI Command | Click the Copy button next to a CLI command. | Command is copied and a success message is displayed. | Copy action worked successfully. | Passed |
| FE-08 | Deploy Lab | Click Deploy Lab. | Deployment result or clear error message is displayed. | Frontend displayed a clear runtime message: `Containerlab is not available in the current backend environment.` | Passed |
| FE-09 | Validation Page Navigation | Click Validate Lab. | User is navigated to the Validation Result page. | Validation Result page opened successfully. | Passed |
| FE-10 | Run Validation | Click Run Validation. | Score, passed checks, failed checks, and recommendations are displayed. | Validation result was displayed successfully. | Passed |
| FE-11 | Recommendation Cards | Review recommendation section. | Topic, priority, related error type, and message are readable. | Recommendation cards were displayed successfully. | Passed |
| FE-12 | Destroy Lab | Click Destroy Lab if available. | Destroy result or clear error message is displayed. | Frontend displayed a clear runtime message when Containerlab was unavailable. | Passed |
| FE-13 | Backend Down Error Handling | Stop the backend and try an API-based action. | Frontend shows a clear backend unreachable error instead of blank screen. | Frontend displayed: `Backend API is not reachable. Please make sure the FastAPI server is running and the API base URL is correct.` | Passed |
| FE-14 | Invalid Session Handling | Try to access or validate an invalid session ID if possible. | Frontend shows a clear invalid session or endpoint error. | Not tested in the current manual demo flow. | Not Tested |

## Browser Debug Checklist

| Area | What to Check | Expected Result | Actual Result | Status |
|---|---|---|---|---|
| Console | JavaScript errors | No unexpected runtime errors | No console error was observed during the tested flow. | Passed |
| Network | API request URLs | Requests should go to the correct backend base URL | Requests used `http://127.0.0.1:8000/api/v1`. | Passed |
| Network | HTTP status codes | 200 for successful requests, clear UI message for errors | Successful requests worked; runtime limitations were displayed clearly. | Passed |
| UI | Empty or undefined values | No visible `undefined`, `null`, or `[object Object]` text | No broken placeholder text was observed. | Passed |
| UI | Language consistency | Demo UI should remain English-only for now | Visible demo UI remained English-only. | Passed |

## Notes

- The frontend uses centralized API error handling.
- Backend, CORS, 404, 422, and 500 errors are displayed with user-friendly messages.
- CLI commands are shown in readable command boxes with copy buttons.
- Validation results show score, check metrics, failed checks, and recommendations.
- Containerlab runtime was not available in the current frontend test environment, but the frontend displayed this condition clearly.
- Backend down error handling was tested successfully.
- This checklist can be used as evidence for the final report testing section.
