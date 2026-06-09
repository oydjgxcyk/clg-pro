# Bugfix Requirements Document

## Introduction

The DOMS (Digital Outpass Management System) is a multi-role college project built with Flask, SQLite, and plain HTML/JS. While the project has a working backend skeleton and styled dashboards for six roles (Student, Mentor, Parent, HOD, Dean, Security), the system is not functional end-to-end. The core problems fall into three categories:

1. **Hardcoded identity data** — every dashboard displays static names, IDs, and statistics that are baked into the HTML instead of being fetched from the backend or read from a login session.
2. **Missing or broken JavaScript functions** — several UI actions (submit form, reset form, load history, load QR) are wired to functions that are never defined, causing silent failures.
3. **Incomplete backend** — missing API routes, a broken static-file configuration, a missing `created_at` timestamp on the data model, and a fragile `qrcode` import prevent the system from running correctly.

Fixing these issues will make every dashboard fully dynamic, driven by real data, and usable without manual code edits.

---

## Bug Analysis

### Current Behavior (Defect)

**Student Dashboard**

1.1 WHEN the student dashboard loads THEN the system displays the hardcoded name "Elakkiya S.", roll number "2021CS01", and department "Computer Science" in the welcome card, top-nav, and apply-form instead of reading them from a login session or localStorage.

1.2 WHEN a student clicks "Submit Request" THEN the system throws a JavaScript ReferenceError because `submitReq()` is never defined, and no outpass is submitted to the backend.

1.3 WHEN a student clicks "Reset Form" THEN the system throws a JavaScript ReferenceError because `resetForm()` is never defined, and the form fields are not cleared.

1.4 WHEN a student navigates to the "Leave History" tab THEN the system throws a JavaScript ReferenceError because `loadHistory()` is never defined, and the history table remains in its "Loading history..." placeholder state forever.

1.5 WHEN a student navigates to the "QR Pass" tab THEN the system throws a JavaScript ReferenceError because `loadQR()` is never defined, and the QR section remains in its "Loading QR pass..." placeholder state forever.

1.6 WHEN the student dashboard renders the attendance circle THEN the system always shows 92% because the value is hardcoded in the CSS (`conic-gradient`) and the `circle-val` span, not fetched from the backend.

1.7 WHEN the student dashboard renders the status tab THEN the system produces broken HTML because the timeline `<div class="time...` tag is truncated mid-attribute, causing a malformed DOM.

1.8 WHEN the notifications panel is opened THEN the system shows three hardcoded static messages ("Mentor Approved", "Parent Verification", "QR Generated") that do not reflect the actual status of the student's real requests.

**Mentor Dashboard**

1.9 WHEN the mentor dashboard loads THEN the system displays the hardcoded name "Prof. Jane Doe" and ID "M-1042" in the header instead of reading them from a login session.

1.10 WHEN a mentor clicks "My Students" in the sidebar THEN the system navigates to `href="#"` and nothing happens, because no student-list view or route exists.

1.11 WHEN the mentor analytics cards load THEN the system shows only "Pending" and "Approved" counts; there is no "Rejected" stat card, so rejected requests are invisible in the analytics.

**Parent Dashboard**

1.12 WHEN the parent dashboard loads THEN the system displays the hardcoded heading "Welcome, Parent of John Doe" instead of reading the linked student's name from the backend.

1.13 WHEN the parent dashboard first renders THEN the system shows hardcoded detail rows ("Family Medical Emergency", "Hometown", "Oct 24, 05:00 PM") and a hardcoded 92% attendance circle before the JavaScript `loadPending()` call replaces them, causing a visible flash of incorrect data.

1.14 WHEN the parent dashboard renders the approval flow timeline THEN the system shows a static hardcoded HTML timeline (Mentor = completed, Parent = active, HOD/Dean = empty) that does not reflect the actual approval state of the current request.

**HOD Dashboard**

1.15 WHEN the HOD dashboard loads THEN the system displays the hardcoded name "Dr. Head of Dept" in the header instead of reading it from a login session.

1.16 WHEN the HOD analytics cards load THEN the system calls `GET /analytics` which returns global counts across all departments, so the Pending/Approved/Rejected numbers shown are not filtered to the HOD's own department.

**Dean Dashboard**

1.17 WHEN the Dean dashboard loads THEN the system displays the hardcoded name "Dr. Robert Smith" in the header instead of reading it from a login session.

1.18 WHEN the live campus monitor loads THEN the system calls `allRequests.slice(-5).reverse()` which limits the monitor to the last 5 requests only, hiding all earlier approved outpasses.

1.19 WHEN the Dean dashboard is open THEN the system does not auto-refresh the live monitor, so newly approved requests do not appear without a manual page reload.

**Security Dashboard**

1.20 WHEN the security dashboard top bar renders THEN the system shows the hardcoded text "42 Live Outside Campus" instead of a count fetched from the backend.

1.21 WHEN the security dashboard top bar renders THEN the system shows the hardcoded timestamp "Oct 24, 2026 - 10:45 AM" instead of the current live date and time.

1.22 WHEN the security dashboard top bar renders THEN the system shows the hardcoded officer name "Officer Davis" instead of reading it from a login session.

1.23 WHEN the security logs tab is opened THEN the system shows three hardcoded static log rows instead of real scan/verification events from the backend.

1.24 WHEN the security analytics charts render THEN the system uses hardcoded data arrays (e.g., `[12, 45, 80, 30, 20, 60, 15]` for exits, `[45, 25, 20, 10]` for departments) instead of data fetched from the backend.

1.25 WHEN `loadLiveMonitor()` runs THEN the system uses `document.querySelector('#dashboard tbody')` as the table body selector, which does not match the actual element `id="liveMonitorBody"`, so the live monitor table is never populated.

1.26 WHEN `loadLiveMonitor()` runs THEN the system does not update the four stat cards (`outsideCount`, `approvedCount`, `rejectedCount`, `pendingCount`), so they remain at "--" indefinitely.

**Backend (app.py)**

1.27 WHEN the Flask app starts THEN the system is configured with `template_folder='templates'` and `static_folder='static'`, but those directories do not exist; page routes use `send_from_directory('.')` instead, creating an inconsistency that will cause static assets (QR images) to fail to serve.

1.28 WHEN the Dean approves a request and a QR image is saved to `static/qr/` THEN the system cannot serve that image because the `static` folder is not present and Flask's static file serving is misconfigured.

1.29 WHEN any dashboard tries to call `GET /dean/reject/<id>` THEN the system returns a 404 because no reject route exists for the Dean role, making it impossible for the Dean to reject a request.

1.30 WHEN the Flask app imports `qrcode` at startup THEN the system raises an `ImportError` if the `qrcode` package is not installed, crashing the entire application before any route is served.

1.31 WHEN a student dashboard or any consumer calls `GET /student/profile` THEN the system returns a 404 because no profile endpoint exists, so dynamic student identity data cannot be fetched.

1.32 WHEN outpass requests are stored THEN the system saves no `created_at` timestamp on the `OutpassRequest` model, so requests cannot be sorted or filtered by submission time and history displays in an arbitrary order.

1.33 WHEN the security dashboard calls for live stats THEN the system returns a 404 because no `GET /security/stats` endpoint exists, so the stat cards cannot be populated dynamically.

---

### Expected Behavior (Correct)

**Student Dashboard**

2.1 WHEN the student dashboard loads THEN the system SHALL read the student's name, roll number, and department from localStorage (set at login) and render them in the welcome card, top-nav, and apply-form fields.

2.2 WHEN a student clicks "Submit Request" THEN the system SHALL call the defined `submitReq()` function, POST the form data to `POST /apply-outpass`, display a success or error message, and redirect the student to the status tab.

2.3 WHEN a student clicks "Reset Form" THEN the system SHALL call the defined `resetForm()` function and clear all editable form fields back to their default/empty state.

2.4 WHEN a student navigates to the "Leave History" tab THEN the system SHALL call the defined `loadHistory()` function, fetch `GET /student-requests?roll_number=<roll>`, and populate the history table with real request records.

2.5 WHEN a student navigates to the "QR Pass" tab THEN the system SHALL call the defined `loadQR()` function, fetch the student's approved requests, and display the QR image for the most recent approved outpass or a "No approved pass" message.

2.6 WHEN the student dashboard renders the attendance circle THEN the system SHALL fetch the student's attendance from `GET /student/profile` and render the circle with the real percentage value.

2.7 WHEN the student dashboard renders the status tab THEN the system SHALL produce valid, complete HTML for the approval timeline with no truncated tags.

2.8 WHEN the notifications panel is opened THEN the system SHALL fetch the student's recent requests and display notification cards that reflect the actual current approval statuses of those requests.

**Mentor Dashboard**

2.9 WHEN the mentor dashboard loads THEN the system SHALL read the mentor's name and ID from localStorage and display them in the header.

2.10 WHEN a mentor clicks "My Students" in the sidebar THEN the system SHALL navigate to a view or route that lists the mentor's assigned students.

2.11 WHEN the mentor analytics cards load THEN the system SHALL display a "Rejected" stat card alongside Pending and Approved, populated with the real rejected count.

**Parent Dashboard**

2.12 WHEN the parent dashboard loads THEN the system SHALL fetch the linked student's name from the backend and display it in the welcome heading dynamically.

2.13 WHEN the parent dashboard first renders THEN the system SHALL show empty/placeholder detail rows and a neutral attendance circle until `loadPending()` completes, with no flash of hardcoded data.

2.14 WHEN the parent dashboard renders the approval flow timeline THEN the system SHALL build the timeline steps dynamically from the current request's `mentor_status`, `parent_status`, `hod_status`, and `dean_status` fields.

**HOD Dashboard**

2.15 WHEN the HOD dashboard loads THEN the system SHALL read the HOD's name from localStorage and display it in the header.

2.16 WHEN the HOD analytics cards load THEN the system SHALL call a department-filtered analytics endpoint (e.g., `GET /analytics?department=<dept>`) so that counts reflect only requests from the HOD's own department.

**Dean Dashboard**

2.17 WHEN the Dean dashboard loads THEN the system SHALL read the Dean's name from localStorage and display it in the header.

2.18 WHEN the live campus monitor loads THEN the system SHALL display all approved outpass requests, not just the last 5.

2.19 WHEN the Dean dashboard is open THEN the system SHALL auto-refresh the live monitor at a regular interval (e.g., every 30 seconds) so newly approved requests appear without a manual reload.

**Security Dashboard**

2.20 WHEN the security dashboard top bar renders THEN the system SHALL fetch the live outside-campus count from `GET /security/stats` and display it in the top bar.

2.21 WHEN the security dashboard top bar renders THEN the system SHALL display the current live date and time using a JavaScript clock that updates every second.

2.22 WHEN the security dashboard top bar renders THEN the system SHALL read the officer's name from localStorage and display it in the top bar.

2.23 WHEN the security logs tab is opened THEN the system SHALL fetch real scan/verification event data from the backend and populate the logs table dynamically.

2.24 WHEN the security analytics charts render THEN the system SHALL fetch real data from the backend (e.g., `GET /analytics`, `GET /security/stats`) and use it to populate the chart datasets.

2.25 WHEN `loadLiveMonitor()` runs THEN the system SHALL use `document.getElementById('liveMonitorBody')` (or `#liveMonitorBody`) as the table body target so the live monitor table is correctly populated.

2.26 WHEN `loadLiveMonitor()` runs THEN the system SHALL update all four stat cards (`outsideCount`, `approvedCount`, `rejectedCount`, `pendingCount`) with values fetched from `GET /security/stats`.

**Backend (app.py)**

2.27 WHEN the Flask app starts THEN the system SHALL use a consistent file-serving strategy: either serve all HTML files via `send_from_directory('.')` (removing the unused `template_folder`/`static_folder` config), or create the `templates/` and `static/` directories and move files into them.

2.28 WHEN the Dean approves a request and a QR image is generated THEN the system SHALL save the image to a directory that Flask can serve, and the returned URL SHALL resolve correctly in the browser.

2.29 WHEN a Dean calls `PUT /dean/reject/<id>` THEN the system SHALL set `dean_status = 'Rejected'` and `final_status = 'Rejected'` on the request and return a success response.

2.30 WHEN the Flask app starts THEN the system SHALL handle a missing `qrcode` package gracefully — either by listing it in `requirements.txt` so it is always installed, or by catching the `ImportError` and disabling QR generation with a clear log message rather than crashing.

2.31 WHEN a student dashboard calls `GET /student/profile` THEN the system SHALL return the authenticated student's name, roll number, department, and attendance percentage.

2.32 WHEN an outpass request is created THEN the system SHALL store a `created_at` timestamp (defaulting to the current UTC time) on the `OutpassRequest` record so that requests can be sorted and filtered by submission time.

2.33 WHEN the security dashboard calls `GET /security/stats` THEN the system SHALL return the count of currently approved (outside-campus) students, total approved, total rejected, and total pending requests.

---

### Unchanged Behavior (Regression Prevention)

3.1 WHEN a mentor calls `PUT /mentor/approve/<id>` or `PUT /mentor/reject/<id>` THEN the system SHALL CONTINUE TO update `mentor_status` correctly and return the existing success response format.

3.2 WHEN a parent calls `PUT /parent/approve/<id>` or `PUT /parent/reject/<id>` THEN the system SHALL CONTINUE TO update `parent_status` correctly and return the existing success response format.

3.3 WHEN a HOD calls `PUT /hod/approve/<id>` or `PUT /hod/reject/<id>` THEN the system SHALL CONTINUE TO update `hod_status` correctly and return the existing success response format.

3.4 WHEN a Dean calls `PUT /dean/approve/<id>` THEN the system SHALL CONTINUE TO set `dean_status = 'Approved'`, `final_status = 'Approved'`, generate a QR code, and return the `qr_file` path in the response.

3.5 WHEN `GET /mentor/pending` is called THEN the system SHALL CONTINUE TO return only requests where `mentor_status = 'Pending'`, including the `risk` classification based on attendance.

3.6 WHEN `GET /parent/pending` is called THEN the system SHALL CONTINUE TO return only requests where `mentor_status = 'Approved'` and `parent_status = 'Pending'`.

3.7 WHEN `GET /hod/pending` is called THEN the system SHALL CONTINUE TO return only requests where `parent_status = 'Approved'` and `hod_status = 'Pending'`.

3.8 WHEN `GET /dean/pending` is called THEN the system SHALL CONTINUE TO return only requests where `hod_status = 'Approved'` and `dean_status = 'Pending'`, including the chain statuses for display.

3.9 WHEN `POST /apply-outpass` is called with valid data THEN the system SHALL CONTINUE TO create a new `OutpassRequest` record and return the new request's `id`.

3.10 WHEN `GET /student-requests` is called with a `roll_number` query parameter THEN the system SHALL CONTINUE TO return only that student's requests; when called without the parameter it SHALL CONTINUE TO return all requests.

3.11 WHEN `GET /analytics` is called THEN the system SHALL CONTINUE TO return `total_requests`, `approved_requests`, `rejected_requests`, and `pending_requests` counts.

3.12 WHEN `GET /security/verify/<id>` is called for a request with `final_status = 'Approved'` THEN the system SHALL CONTINUE TO return `{"status": "VALID"}` along with the student's details.

3.13 WHEN `POST /register` is called with a new email THEN the system SHALL CONTINUE TO hash the password and create the user record; duplicate emails SHALL CONTINUE TO return a 409 response.

3.14 WHEN `POST /login` is called with valid credentials THEN the system SHALL CONTINUE TO return a JWT token, the user's role, and the user's name.

3.15 WHEN the index portal page (`/`) is loaded THEN the system SHALL CONTINUE TO display all six role cards linking to their respective dashboard routes.

3.16 WHEN the HOD dashboard calls `PUT /hod/reject/<id>` THEN the system SHALL CONTINUE TO set both `hod_status = 'Rejected'` and `final_status = 'Rejected'`.

3.17 WHEN the mentor dashboard's approval card is rendered THEN the system SHALL CONTINUE TO display the attendance progress bar with the correct risk color (green/yellow/red) based on the attendance threshold logic.

3.18 WHEN the parent dashboard's `confirmAction()` is called THEN the system SHALL CONTINUE TO remove the processed request from the local queue and show the "Next Pending Request" button if more requests remain.
