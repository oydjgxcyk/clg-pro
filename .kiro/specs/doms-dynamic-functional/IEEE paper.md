# Implementation Plan

## Overview

This task list follows the exploratory bugfix workflow for the DOMS Dynamic Functional spec. Tasks are ordered: explore (write tests on unfixed code), preserve (baseline tests), implement (backend then each dashboard), validate (re-run tests), checkpoint.

## Tasks

- [x] 1. Write bug condition exploration test
  - **Property 1: Bug Condition** - Hardcoded Identity, Undefined JS Functions, Missing Routes
  - **CRITICAL**: This test MUST FAIL on unfixed code — failure confirms the bugs exist
  - **DO NOT attempt to fix the test or the code when it fails**
  - **GOAL**: Surface counterexamples that demonstrate each bug category exists
  - **Scoped PBT Approach**: Scope to concrete failing cases for each bug condition
  - Test A — Backend routes: call `GET /student/profile`, `PUT /dean/reject/1`, `GET /security/stats` on the unfixed app; assert each returns HTTP 200 (not 404)
  - Test B — Model field: query `OutpassRequest` columns; assert `created_at` exists in the column list
  - Test C — App startup: attempt to import `app.py` with `qrcode` absent; assert no `ImportError` is raised
  - Test D — Static folder: assert `static/qr/` directory exists so Flask can serve QR images
  - Test E — JS functions: parse `student_dashboard.html`; assert `submitReq`, `resetForm`, `loadHistory`, `loadQR` are all defined (not just referenced in `onclick`)
  - Test F — Hardcoded strings: parse each dashboard HTML; assert none contain the literal strings `"Elakkiya S."`, `"Prof. Jane Doe"`, `"Dr. Robert Smith"`, `"Dr. Head of Dept"`, `"Officer Davis"`, `"John Doe"`
  - Run all tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests FAIL (this is correct — it proves the bugs exist)
  - Document counterexamples found (e.g., `GET /student/profile` → 404, `submitReq` not found in script block)
  - Mark task complete when tests are written, run, and failures are documented
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.9, 1.12, 1.15, 1.17, 1.20, 1.22, 1.25, 1.27, 1.29, 1.30, 1.31, 1.32, 1.33_


- [ ] 2. Write preservation property tests (BEFORE implementing fix)
  - **Property 2: Preservation** - Existing API Contracts and UI Interactions Unchanged
  - **IMPORTANT**: Follow observation-first methodology
  - Observe on UNFIXED code: `PUT /mentor/approve/1` → `{"message": "Approved By Mentor"}` with HTTP 200
  - Observe on UNFIXED code: `PUT /mentor/reject/1` → `{"message": "Rejected By Mentor"}` with HTTP 200
  - Observe on UNFIXED code: `PUT /parent/approve/1`, `PUT /parent/reject/1` → correct JSON + HTTP 200
  - Observe on UNFIXED code: `PUT /hod/approve/1`, `PUT /hod/reject/1` → correct JSON + HTTP 200
  - Observe on UNFIXED code: `PUT /dean/approve/1` → sets `final_status='Approved'`, returns `qr_file` key
  - Observe on UNFIXED code: `POST /apply-outpass` → returns `{"id": <int>}` with HTTP 200
  - Observe on UNFIXED code: `GET /student-requests?roll_number=X` → returns array filtered by roll
  - Observe on UNFIXED code: `GET /analytics` → returns `total_requests`, `approved_requests`, `rejected_requests`, `pending_requests`
  - Observe on UNFIXED code: `GET /security/verify/<id>` for approved request → `{"status": "VALID"}` with student fields
  - Observe on UNFIXED code: `POST /register` with new email → HTTP 200; duplicate email → HTTP 409
  - Observe on UNFIXED code: `POST /login` with valid credentials → returns `token`, `role`, `name`
  - Write property-based tests asserting all observed response shapes hold for any valid input
  - Run tests on UNFIXED code
  - **EXPECTED OUTCOME**: Tests PASS (confirms baseline behavior to preserve)
  - Mark task complete when tests are written, run, and passing on unfixed code
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14, 3.15, 3.16, 3.17, 3.18_


- [ ] 3. Fix backend — app.py, requirements.txt, and static folder

  - [~] 3.1 Make `qrcode` import graceful and add `requirements.txt`
    - Replace `import qrcode` at line 7 with a try/except block that sets `QR_AVAILABLE = True/False`
    - Guard the QR generation block inside `dean_approve` with `if QR_AVAILABLE:`
    - Create `requirements.txt` in the project root listing: Flask, Flask-SQLAlchemy, Flask-CORS, Flask-JWT-Extended, Werkzeug, qrcode[pil], Pillow with pinned versions
    - _Bug_Condition: isBugCondition({type:'app_startup'}) where qrcode not installed_
    - _Expected_Behavior: app starts without ImportError; QR generation disabled with log warning_
    - _Preservation: dean/approve route continues to generate QR when qrcode IS installed_
    - _Requirements: 2.30_

  - [~] 3.2 Create `static/qr/` directory and fix static-file configuration
    - Add `os.makedirs('static/qr', exist_ok=True)` at module level (after app creation) so the directory is always present
    - Remove the unused `template_folder='templates'` argument from `Flask(...)` since all HTML is served via `send_from_directory('.')`; keep `static_folder='static'` so `/static/qr/<file>` resolves correctly
    - _Bug_Condition: isBugCondition({type:'app_startup'}) where static/ does not exist_
    - _Expected_Behavior: QR images saved to static/qr/ are served at /static/qr/<filename>_
    - _Preservation: all six page routes using send_from_directory('.') continue to work_
    - _Requirements: 2.27, 2.28_

  - [~] 3.3 Add `created_at` column to `OutpassRequest` model
    - Add `from datetime import datetime` import at the top of app.py
    - Add `created_at = db.Column(db.DateTime, default=datetime.utcnow)` to the `OutpassRequest` class
    - Include `created_at` (ISO-formatted) in the serialized dict returned by `student_requests()` and `dean_pending()`
    - _Bug_Condition: isBugCondition({type:'app_startup'}) where created_at column missing_
    - _Expected_Behavior: new requests store UTC timestamp; history can be sorted chronologically_
    - _Preservation: POST /apply-outpass and GET /student-requests continue to work; existing fields unchanged_
    - _Requirements: 2.32_

  - [~] 3.4 Add `GET /student/profile` route
    - Add route that accepts `?roll_number=` query param
    - Query `OutpassRequest` records for that roll number; compute average attendance
    - Return JSON: `{name, roll_number, department, attendance}`
    - Return 200 with empty/default values when no records exist (do not 404)
    - _Bug_Condition: isBugCondition({type:'api_call', endpoint:'GET /student/profile'})_
    - _Expected_Behavior: returns student identity + attendance; HTTP 200_
    - _Preservation: no existing routes affected_
    - _Requirements: 2.31_

  - [~] 3.5 Add `PUT /dean/reject/<id>` route
    - Add route following the same pattern as `mentor_reject`, `parent_reject`, `hod_reject`
    - Set `req.dean_status = 'Rejected'` and `req.final_status = 'Rejected'`
    - Return `{"message": "Rejected By Dean"}` on success; 404 when id not found
    - _Bug_Condition: isBugCondition({type:'api_call', endpoint:'PUT /dean/reject/<id>'})_
    - _Expected_Behavior: dean_status and final_status set to Rejected; HTTP 200_
    - _Preservation: PUT /dean/approve continues to set Approved and generate QR_
    - _Requirements: 2.29_

  - [~] 3.6 Add `GET /security/stats` route
    - Add route that counts: `outside_count` (final_status=Approved), `approved_count` (same), `rejected_count` (final_status=Rejected), `pending_count` (total minus approved minus rejected)
    - Return JSON with those four keys
    - _Bug_Condition: isBugCondition({type:'api_call', endpoint:'GET /security/stats'})_
    - _Expected_Behavior: returns four stat counts; HTTP 200_
    - _Preservation: GET /analytics continues to return its existing four keys unchanged_
    - _Requirements: 2.33_

  - [~] 3.7 Add optional `?department=` filter to `GET /analytics`
    - Read `dept = request.args.get('department', '')` at the top of the `analytics()` function
    - If `dept` is non-empty, add `.filter_by(department=dept)` to the base query before counting
    - When `dept` is empty the route behaves exactly as before (global counts)
    - _Bug_Condition: isBugCondition({type:'page_load'}) for HOD dashboard showing global analytics_
    - _Expected_Behavior: GET /analytics?department=CS returns counts only for CS department_
    - _Preservation: GET /analytics (no param) continues to return global counts — Requirement 3.11_
    - _Requirements: 2.16, 3.11_


- [ ] 4. Fix student_dashboard.html

  - [~] 4.1 Replace hardcoded identity constants with localStorage reads
    - At the top of the `<script>` block, replace the three hardcoded constants:
      - `const ROLL = localStorage.getItem('roll_number') || '';`
      - `const STUDENT_NAME = localStorage.getItem('name') || 'Student';`
      - `const DEPT = localStorage.getItem('department') || '';`
    - On `DOMContentLoaded`, write these values into the DOM: top-nav name span, welcome heading, roll/dept display spans, and the apply-form readonly input fields
    - _Bug_Condition: isBugCondition({type:'page_load'}) where dashboard renders hardcoded "Elakkiya S." / "2021CS01"_
    - _Expected_Behavior: identity values read from localStorage and rendered dynamically_
    - _Requirements: 2.1_

  - [~] 4.2 Define `submitReq(btn)` function
    - Add the full `async function submitReq(btn)` implementation in the `<script>` block
    - Validate all required fields (reason, destination, exit_time, return_time); show warning if empty
    - Disable button and show spinner while submitting
    - POST to `${API}/apply-outpass` with student identity fields from ROLL/STUDENT_NAME/DEPT constants
    - On success: show success alert with request ID; after 1.5 s switch to status tab via `switchTab()`
    - On error: re-enable button; show error alert
    - _Bug_Condition: isBugCondition({type:'button_click', handler:'submitReq'})_
    - _Expected_Behavior: function defined; POSTs to /apply-outpass; shows result message_
    - _Requirements: 2.2_

  - [~] 4.3 Define `resetForm()` function
    - Add `function resetForm()` that clears reason, destination, exit_time, return_time, contact fields
    - Hide the `#formMsg` div
    - _Bug_Condition: isBugCondition({type:'button_click', handler:'resetForm'})_
    - _Expected_Behavior: function defined; all form fields cleared_
    - _Requirements: 2.3_

  - [~] 4.4 Define `loadHistory()` function
    - Add `async function loadHistory()` that fetches `GET ${API}/student-requests?roll_number=${ROLL}`
    - Show loading row while fetching; populate `#historyBody` with one `<tr>` per request (date from `created_at`, reason, exit_time, return_time, QR status, final badge)
    - Show "No history yet" row when array is empty; show error row on fetch failure
    - _Bug_Condition: isBugCondition({type:'button_click', handler:'loadHistory'})_
    - _Expected_Behavior: function defined; history table populated from real data_
    - _Requirements: 2.4_

  - [~] 4.5 Define `loadQR()` function
    - Add `async function loadQR()` that fetches student requests and filters for `status === 'Approved'`
    - If no approved request: show "No approved outpass" message in `#qrContent`
    - If approved: render `<img src="${API}/static/qr/qr_${latest.id}.png">` with an `onerror` fallback message
    - _Bug_Condition: isBugCondition({type:'button_click', handler:'loadQR'})_
    - _Expected_Behavior: function defined; QR image or fallback message shown_
    - _Requirements: 2.5_

  - [~] 4.6 Wire dynamic attendance circle to `GET /student/profile`
    - Inside `loadDashboard()`, after the existing fetch, also call `GET ${API}/student/profile?roll_number=${ROLL}`
    - Update `#attendancePct` text content and the `conic-gradient` CSS with the returned `attendance` value
    - _Bug_Condition: isBugCondition({type:'page_load'}) where attendance circle shows hardcoded 92%_
    - _Expected_Behavior: attendance circle shows real percentage from backend_
    - _Requirements: 2.6_

  - [~] 4.7 Fix broken timeline HTML in status tab
    - Locate the truncated `<div class="time...` tag in the status tab static HTML
    - Remove the broken static placeholder entirely; replace with an empty `<div id="statusList"></div>`
    - Confirm the existing `loadStatus()` JS function already populates `#statusList` dynamically (no JS change needed)
    - _Bug_Condition: isBugCondition({type:'page_load'}) where status tab has malformed DOM_
    - _Expected_Behavior: valid HTML; timeline rendered by loadStatus() JS_
    - _Requirements: 2.7_

  - [~] 4.8 Replace hardcoded notification cards with dynamic ones
    - Remove the three static `<div class="notif-card">` elements from the notifications panel
    - Add `<div id="notifList"></div>` placeholder
    - On notifications panel open (or on `DOMContentLoaded`), fetch student requests and render one card per request showing its current approval status
    - _Bug_Condition: isBugCondition({type:'page_load'}) where notifications show hardcoded static messages_
    - _Expected_Behavior: notification cards reflect actual request statuses_
    - _Requirements: 2.8_


- [ ] 5. Fix mentor_dashboard.html

  - [~] 5.1 Read mentor identity from localStorage on load
    - Add `DOMContentLoaded` listener that reads `localStorage.getItem('name')` (fallback `'Mentor'`)
    - Write the name into the header element that currently shows `"Prof. Jane Doe"`
    - Derive initials (first two capital letters) and write into `.profile-avatar`
    - Remove the hardcoded `"M-1042"` ID string or replace it with a localStorage read if an ID key is stored
    - _Bug_Condition: isBugCondition({type:'page_load'}) where header shows hardcoded "Prof. Jane Doe"_
    - _Expected_Behavior: header shows name from localStorage_
    - _Requirements: 2.9_

  - [~] 5.2 Add "Rejected" stat card to analytics grid
    - Add a third `<div class="stat-card">` with `id="rejectedCount"` to the `.analytics-grid`
    - In `loadPending()`, after populating `pendingCount` and `approvedCount`, also set `document.getElementById('rejectedCount').textContent = analytics.rejected_requests`
    - _Bug_Condition: isBugCondition({type:'page_load'}) where rejected count is invisible_
    - _Expected_Behavior: three stat cards shown — Pending, Approved, Rejected_
    - _Requirements: 2.11_

  - [~] 5.3 Implement "My Students" view
    - Change the sidebar "My Students" link from `href="#"` to `onclick="loadMyStudents()"`
    - Define `async function loadMyStudents()` that fetches `GET ${API}/student-requests`
    - Render a deduplicated list of student names and roll numbers in the `#requestsGrid` area (or a dedicated panel)
    - _Bug_Condition: isBugCondition({type:'page_load'}) where My Students link does nothing_
    - _Expected_Behavior: clicking My Students shows list of students with pending/approved requests_
    - _Requirements: 2.10_


- [ ] 6. Fix parent_dashboard.html

  - [~] 6.1 Remove hardcoded flash data from initial HTML
    - Replace the static `.details-card` rows that show `"Family Medical Emergency"`, `"Hometown"`, `"Oct 24, 05:00 PM"` with empty `<td>` cells or `"—"` placeholders
    - Replace the hardcoded 92% attendance circle value with a neutral `"—"` or `0%` placeholder
    - The existing `showRequest()` JS function already overwrites these fields dynamically — this task ensures no incorrect data flashes before `loadPending()` completes
    - _Bug_Condition: isBugCondition({type:'page_load'}) where hardcoded detail rows flash before JS loads_
    - _Expected_Behavior: initial render shows empty/neutral placeholders; showRequest() fills real data_
    - _Requirements: 2.13_

  - [~] 6.2 Make welcome heading dynamic
    - Remove the hardcoded `"Welcome, Parent of John Doe 👋"` string from the HTML
    - Inside `showRequest(r)`, after `r` is set, write: `document.querySelector('.welcome-card h1').textContent = 'Welcome, Parent of ' + r.student_name + ' 👋'`
    - Also update the department subtitle: `document.querySelector('.welcome-card p').textContent = r.department + ' Dept'`
    - _Bug_Condition: isBugCondition({type:'page_load'}) where heading shows hardcoded "John Doe"_
    - _Expected_Behavior: heading shows actual student name from pending request_
    - _Requirements: 2.12_

  - [~] 6.3 Replace hardcoded approval timeline with dynamic one
    - Remove the static `<div class="steps">` HTML that always shows Mentor=completed, Parent=active
    - Add `<div id="timelineSteps" class="steps"></div>` placeholder
    - Inside `showRequest(r)`, build timeline HTML from `r.mentor_status`, `r.parent_status`, `r.hod_status`, `r.dean_status` — mark each step as completed/active/pending based on its status value
    - _Bug_Condition: isBugCondition({type:'page_load'}) where timeline is always hardcoded Mentor=done, Parent=active_
    - _Expected_Behavior: timeline reflects actual approval chain state of the current request_
    - _Preservation: confirmAction() queue logic (remove processed request, show Next button) unchanged — Requirement 3.18_
    - _Requirements: 2.14, 3.18_


- [ ] 7. Fix hod_dashboard.html

  - [~] 7.1 Read HOD identity from localStorage on load
    - Add `DOMContentLoaded` listener that reads `localStorage.getItem('name')` (fallback `'HOD'`) and `localStorage.getItem('department')` (fallback `'Computer Science'`)
    - Write name into the header element that currently shows `"Dr. Head of Dept"`
    - Write `"HOD • " + dept` into the role/department subtitle element
    - Store `dept` in a module-level variable for use in the analytics fetch
    - _Bug_Condition: isBugCondition({type:'page_load'}) where header shows hardcoded "Dr. Head of Dept"_
    - _Expected_Behavior: header shows HOD name and department from localStorage_
    - _Requirements: 2.15_

  - [~] 7.2 Filter analytics by HOD's department
    - In `loadPending()`, change the analytics fetch from `GET ${API}/analytics` to `GET ${API}/analytics?department=${encodeURIComponent(dept)}`
    - The `dept` variable comes from the localStorage read in task 7.1
    - _Bug_Condition: isBugCondition({type:'page_load'}) where analytics show global counts instead of department counts_
    - _Expected_Behavior: Pending/Approved/Rejected counts reflect only the HOD's department_
    - _Preservation: GET /analytics without ?department param continues to return global counts_
    - _Requirements: 2.16, 3.11_


- [ ] 8. Fix dean_dashboard.html

  - [~] 8.1 Read Dean identity from localStorage on load
    - Add `DOMContentLoaded` listener that reads `localStorage.getItem('name')` (fallback `'Dean'`)
    - Write name into the header element that currently shows `"Dr. Robert Smith"`
    - Call `loadDashboard()` from within the listener (replacing any existing inline call)
    - _Bug_Condition: isBugCondition({type:'page_load'}) where header shows hardcoded "Dr. Robert Smith"_
    - _Expected_Behavior: header shows Dean name from localStorage_
    - _Requirements: 2.17_

  - [~] 8.2 Show all approved requests in live monitor (remove `.slice(-5)`)
    - In `loadDashboard()`, locate `allRequests.slice(-5).reverse()`
    - Replace with `allRequests.filter(r => r.status === 'Approved').reverse()` to show all approved outpasses
    - _Bug_Condition: isBugCondition({type:'page_load'}) where monitor is capped at last 5 requests_
    - _Expected_Behavior: all approved outpass requests are shown in the live monitor_
    - _Requirements: 2.18_

  - [~] 8.3 Add 30-second auto-refresh for live monitor
    - After calling `loadDashboard()` in the `DOMContentLoaded` listener, add `setInterval(loadDashboard, 30000)`
    - _Bug_Condition: isBugCondition({type:'page_load'}) where dashboard never auto-refreshes_
    - _Expected_Behavior: live monitor refreshes every 30 seconds without manual reload_
    - _Requirements: 2.19_

  - [~] 8.4 Add Reject button to each approval card
    - In the approval card rendering loop inside `loadDashboard()`, add a Reject button alongside the existing "Grant & Generate QR" button
    - Button calls `rejectApproval(r.id)` on click
    - Define `async function rejectApproval(id)` that calls `PUT ${API}/dean/reject/${id}` then calls `setTimeout(loadDashboard, 500)`
    - _Bug_Condition: isBugCondition({type:'api_call', endpoint:'PUT /dean/reject/<id>'}) — no UI trigger existed_
    - _Expected_Behavior: Dean can reject a request; card disappears from pending list after rejection_
    - _Preservation: PUT /dean/approve continues to work and generate QR — Requirement 3.4_
    - _Requirements: 2.29, 3.4_


- [ ] 9. Fix security_dashboard.html

  - [~] 9.1 Fix `#liveMonitorBody` DOM selector
    - In `loadLiveMonitor()`, replace `document.querySelector('#dashboard tbody')` with `document.getElementById('liveMonitorBody')`
    - _Bug_Condition: isBugCondition({type:'page_load'}) where querySelector returns null and table is never populated_
    - _Expected_Behavior: live monitor table body is correctly targeted and populated_
    - _Requirements: 2.25_

  - [~] 9.2 Fetch and display stat cards from `GET /security/stats`
    - In `loadLiveMonitor()`, after the existing fetch, also call `GET ${API}/security/stats`
    - Write `stats.outside_count`, `stats.approved_count`, `stats.rejected_count`, `stats.pending_count` into the corresponding `#outsideCount`, `#approvedCount`, `#rejectedCount`, `#pendingCount` elements
    - _Bug_Condition: isBugCondition({type:'page_load'}) where stat cards remain at "--"_
    - _Expected_Behavior: all four stat cards show real counts from backend_
    - _Requirements: 2.26, 2.20_

  - [~] 9.3 Read officer name from localStorage
    - On `DOMContentLoaded`, read `localStorage.getItem('name')` (fallback `'Security Officer'`)
    - Write the name into the top-bar element that currently shows `"Officer Davis"`
    - _Bug_Condition: isBugCondition({type:'page_load'}) where top bar shows hardcoded "Officer Davis"_
    - _Expected_Behavior: officer name read from localStorage_
    - _Requirements: 2.22_

  - [~] 9.4 Add live clock to top bar
    - Define `function updateClock()` that writes `new Date().toLocaleString()` into the top-bar timestamp element that currently shows `"Oct 24, 2026 - 10:45 AM"`
    - Call `updateClock()` immediately on `DOMContentLoaded` and then `setInterval(updateClock, 1000)`
    - _Bug_Condition: isBugCondition({type:'page_load'}) where timestamp is hardcoded static string_
    - _Expected_Behavior: timestamp shows current live date/time, updating every second_
    - _Requirements: 2.21_

  - [~] 9.5 Replace hardcoded chart data with backend data
    - In the Chart.js initialization blocks, replace the hardcoded `data` arrays with values fetched from `GET ${API}/analytics` and `GET ${API}/security/stats`
    - For the department pie chart, use `approved_count`, `rejected_count`, `pending_count` from `/security/stats` as a proxy until a dedicated breakdown endpoint exists
    - For the exit timing bar chart, use the approved count as a single data point or distribute evenly across time slots as a placeholder
    - _Bug_Condition: isBugCondition({type:'page_load'}) where charts show hardcoded static arrays_
    - _Expected_Behavior: chart datasets populated from real backend data_
    - _Requirements: 2.24_

  - [~] 9.6 Replace hardcoded security log rows with dynamic data
    - Remove the three static `<tr>` rows from the logs tab
    - Add `<tbody id="logsBody"></tbody>` placeholder
    - On logs tab open (or `DOMContentLoaded`), fetch `GET ${API}/student-requests` and render one row per request showing student name, roll, destination, exit_time, and final_status as a scan event
    - _Bug_Condition: isBugCondition({type:'page_load'}) where logs tab shows hardcoded static rows_
    - _Expected_Behavior: logs table populated from real request data_
    - _Requirements: 2.23_


- [ ] 10. Fix for all dashboards — verify bug condition exploration test now passes

  - [~] 10.1 Verify bug condition exploration test now passes
    - **Property 1: Expected Behavior** - Dynamic Identity, Defined Functions, Complete Backend
    - **IMPORTANT**: Re-run the SAME tests from task 1 — do NOT write new tests
    - The tests from task 1 encode the expected behavior
    - When these tests pass, it confirms the expected behavior is satisfied
    - Run all six test cases (A through F) from task 1 on the FIXED code
    - **EXPECTED OUTCOME**: All tests PASS (confirms all bugs are fixed)
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.9, 2.12, 2.15, 2.17, 2.20, 2.22, 2.25, 2.27, 2.29, 2.30, 2.31, 2.32, 2.33_

  - [~] 10.2 Verify preservation tests still pass
    - **Property 2: Preservation** - Existing API Contracts and UI Interactions Unchanged
    - **IMPORTANT**: Re-run the SAME tests from task 2 — do NOT write new tests
    - Run all preservation property tests from task 2 on the FIXED code
    - **EXPECTED OUTCOME**: All tests PASS (confirms no regressions)
    - Confirm all existing routes return the same response shapes as observed on unfixed code
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14, 3.15, 3.16, 3.17, 3.18_

- [~] 11. Checkpoint — Ensure all tests pass
  - Run the full test suite (exploration + preservation tests)
  - Manually verify each dashboard in the browser: load each page, confirm identity shows from localStorage, confirm all buttons work without ReferenceError
  - Verify the Flask app starts cleanly with and without the `qrcode` package installed
  - Verify `GET /student/profile`, `PUT /dean/reject/1`, `GET /security/stats` all return HTTP 200
  - Verify `static/qr/` directory exists and a QR image is served correctly after dean approval
  - Ensure all tests pass; ask the user if questions arise.

## Task Dependency Graph

```json
{
  "waves": [
    { "wave": 1, "tasks": ["1", "2"] },
    { "wave": 2, "tasks": ["3"] },
    { "wave": 3, "tasks": ["4", "5", "6", "7", "8", "9"] },
    { "wave": 4, "tasks": ["10"] },
    { "wave": 5, "tasks": ["11"] }
  ]
}
```

- Tasks 1 and 2 are independent of each other and can be written in parallel.
- Tasks 3–9 (implementation) depend on tasks 1 and 2 being complete.
- Task 3 (backend) should be completed before tasks 4–9 (dashboards) since the dashboards call the new routes.
- Tasks 4–9 are independent of each other and can be implemented in parallel.
- Tasks 10 and 11 depend on all implementation tasks (3–9) being complete.

## Notes

- All property-based tests (tasks 1 and 2) must be written and run on the **unfixed** code before any implementation begins.
- Task 1 tests are expected to FAIL on unfixed code — this is the correct outcome confirming the bugs exist.
- Task 2 tests are expected to PASS on unfixed code — this establishes the preservation baseline.
- The `created_at` column (task 3.3) requires a fresh database or manual `ALTER TABLE` for existing databases; `db.create_all()` handles it for new databases.
- The `?department=` filter on `/analytics` (task 3.7) is backward-compatible — callers without the param get the same global counts as before.
- Each dashboard fix is self-contained; a failure in one dashboard does not block fixes to others.
