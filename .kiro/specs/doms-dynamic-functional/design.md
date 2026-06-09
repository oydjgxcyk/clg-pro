# DOMS Dynamic Functional Bugfix Design

## Overview

The DOMS (Digital Outpass Management System) has a working Flask/SQLite backend and six styled HTML dashboards, but the system is not functional end-to-end. Three categories of defects prevent it from working:

1. **Hardcoded identity data** — every dashboard renders static names, IDs, and statistics baked into the HTML instead of reading from a login session stored in localStorage.
2. **Missing JavaScript functions** — `submitReq()`, `resetForm()`, `loadHistory()`, and `loadQR()` are called from button `onclick` handlers in `student_dashboard.html` but are never defined, causing silent `ReferenceError` crashes.
3. **Incomplete backend** — missing API routes (`GET /student/profile`, `PUT /dean/reject/<id>`, `GET /security/stats`), a broken static-file configuration, a missing `created_at` field on `OutpassRequest`, and a fragile top-level `import qrcode` that crashes the app if the package is absent.

The fix strategy is minimal and targeted: add the missing backend routes and model field, correct the Flask static-file configuration, define the missing JS functions, and replace every hardcoded identity value with a localStorage read. No existing routes, database schema migrations for existing columns, or working UI interactions are changed.


## Glossary

- **Bug_Condition (C)**: The set of runtime situations that cause the system to fail — hardcoded identity values, undefined JS functions, missing API routes, broken static-file serving, or a missing model field.
- **Property (P)**: The desired correct behavior — every dashboard reads identity from localStorage, every JS function is defined and calls the correct API, every required route returns the correct response, and static files are served correctly.
- **Preservation**: All existing working behavior that must remain unchanged — the six approval routes (`mentor/approve`, `mentor/reject`, `parent/approve`, `parent/reject`, `hod/approve`, `hod/reject`, `dean/approve`), the `POST /apply-outpass`, `GET /student-requests`, `GET /analytics`, `GET /security/verify/<id>`, `POST /register`, and `POST /login` endpoints, plus all existing UI interactions (approval cards, attendance progress bars, `confirmAction()` in the parent dashboard).
- **localStorage session**: A key/value store in the browser set at login time. Keys used: `name`, `role`, `roll_number`, `department`, `token`. Each dashboard reads these on `DOMContentLoaded`.
- **OutpassRequest**: The SQLAlchemy model in `app.py` representing a student outpass. Currently missing a `created_at` timestamp column.
- **`isBugCondition(input)`**: Pseudocode predicate — returns `true` when the input triggers any of the defects described above.
- **`expectedBehavior(result)`**: Pseudocode predicate — returns `true` when the result matches the correct dynamic behavior described in the requirements.


## Bug Details

### Bug Condition

The bug manifests across three layers: the Flask backend, the browser localStorage session, and the dashboard JavaScript. The system fails when any of the following conditions hold at runtime.

**Formal Specification:**

```
FUNCTION isBugCondition(input)
  INPUT: input — one of { page_load, button_click, api_call, app_startup }
  OUTPUT: boolean

  IF input.type = 'page_load' THEN
    RETURN localStorage.getItem('name') is NOT read by the dashboard
           OR dashboard renders hardcoded identity string

  IF input.type = 'button_click' THEN
    RETURN input.handler IN ['submitReq', 'resetForm', 'loadHistory', 'loadQR']
           AND TYPEOF window[input.handler] = 'undefined'

  IF input.type = 'api_call' THEN
    RETURN input.endpoint IN [
             'GET /student/profile',
             'PUT /dean/reject/<id>',
             'GET /security/stats'
           ]

  IF input.type = 'app_startup' THEN
    RETURN (qrcode package NOT installed AND import qrcode at top-level)
           OR (static/ directory does NOT exist AND Flask static_folder='static')
           OR OutpassRequest.created_at column does NOT exist

  RETURN false
END FUNCTION
```

### Examples

- **Student dashboard load**: Page renders `"Welcome Back, Elakkiya 👋"` and `"2021CS01"` hardcoded in HTML — expected: reads `localStorage.getItem('name')` and `localStorage.getItem('roll_number')`.
- **Submit Request click**: `onclick="submitReq(this)"` fires → `Uncaught ReferenceError: submitReq is not defined` — expected: function is defined, POSTs to `/apply-outpass`, shows success message.
- **Leave History tab**: `loadHistory()` called → `ReferenceError` — expected: fetches `GET /student-requests?roll_number=<roll>` and populates `#historyBody`.
- **Dean reject**: `PUT /dean/reject/5` → HTTP 404 — expected: sets `dean_status='Rejected'`, `final_status='Rejected'`, returns `{"message": "Rejected By Dean"}`.
- **Flask startup without qrcode**: `ImportError: No module named 'qrcode'` crashes the entire app before any route is served — expected: graceful fallback with a log warning.
- **Security live monitor**: `document.querySelector('#dashboard tbody')` returns `null` because the actual element has `id="liveMonitorBody"` — expected: `document.getElementById('liveMonitorBody')` correctly targets the table body.


## Expected Behavior

### Preservation Requirements

**Unchanged Behaviors:**
- `PUT /mentor/approve/<id>` and `PUT /mentor/reject/<id>` continue to update `mentor_status` and return the existing JSON response format.
- `PUT /parent/approve/<id>` and `PUT /parent/reject/<id>` continue to update `parent_status` correctly.
- `PUT /hod/approve/<id>` and `PUT /hod/reject/<id>` continue to update `hod_status` and `final_status` correctly.
- `PUT /dean/approve/<id>` continues to set `dean_status='Approved'`, `final_status='Approved'`, generate a QR code, and return `qr_file` in the response.
- `GET /mentor/pending`, `GET /parent/pending`, `GET /hod/pending`, `GET /dean/pending` continue to return the correct filtered lists with all existing fields.
- `POST /apply-outpass` continues to create a new `OutpassRequest` and return `{"id": <new_id>}`.
- `GET /student-requests` continues to return all requests or filter by `roll_number` query param.
- `GET /analytics` continues to return `total_requests`, `approved_requests`, `rejected_requests`, `pending_requests`.
- `GET /security/verify/<id>` continues to return `{"status": "VALID"}` with student details for approved requests.
- `POST /register` and `POST /login` continue to work with the same request/response contracts.
- The mentor dashboard's attendance progress bar risk-color logic (green/yellow/red) remains unchanged.
- The parent dashboard's `confirmAction()` queue logic (remove processed request, show "Next Pending Request" button) remains unchanged.
- All six page routes (`/`, `/student`, `/mentor`, `/parent`, `/hod`, `/dean`, `/security`) continue to serve their HTML files via `send_from_directory('.')`.

**Scope:**
All inputs that do NOT involve the bug conditions listed above are completely unaffected by this fix. This includes all existing API calls from working dashboards, all approval/rejection flows, and all existing UI interactions that already function correctly.


## Hypothesized Root Cause

Based on direct inspection of `app.py` and all six dashboard HTML files:

1. **Hardcoded identity strings in HTML**: Every dashboard was built with placeholder data (`"Elakkiya S."`, `"Prof. Jane Doe"`, `"Dr. Robert Smith"`, etc.) written directly into the HTML. No login flow was wired to write session data to localStorage, and no dashboard reads from localStorage on load. The `POST /login` endpoint already returns `name`, `role`, and a JWT token — the missing piece is the client-side code to store and read these values.

2. **Missing JS function definitions in student dashboard**: The apply-outpass form buttons call `submitReq()`, `resetForm()`, and the tab-switch handler calls `loadHistory()` and `loadQR()`. Searching `student_dashboard.html` confirms none of these four functions are defined anywhere in the `<script>` block. The existing `loadDashboard()`, `loadStatus()`, and `switchTab()` functions are defined and work correctly — the missing four were simply never written.

3. **Missing backend routes**:
   - `GET /student/profile` — not present in `app.py`. The `User` model has `name`, `email`, `role`, `department` but no `attendance` field; the profile endpoint needs to return identity fields plus a computed or stored attendance value.
   - `PUT /dean/reject/<id>` — not present. The pattern exists for mentor, parent, and HOD reject routes; the dean reject route was omitted.
   - `GET /security/stats` — not present. The security dashboard stat cards (`outsideCount`, `approvedCount`, `rejectedCount`, `pendingCount`) need a dedicated endpoint.

4. **Broken static-file configuration**: `app.py` line 11 sets `static_folder='static'` but the `static/` directory does not exist in the project root. The page routes correctly use `send_from_directory('.')` to serve HTML files, but `dean/approve` saves QR images to `static/qr/` and returns `/static/qr/<filename>` — Flask will serve this path only if the `static/` folder exists and is configured correctly.

5. **Top-level `import qrcode`**: Line 7 of `app.py` imports `qrcode` unconditionally. If the package is not installed (e.g., fresh clone without `pip install`), the entire Flask app fails to start. A `requirements.txt` file is also absent, so there is no documented dependency list.

6. **Missing `created_at` on `OutpassRequest`**: The model has no timestamp column. History and status tabs display requests in arbitrary database insertion order. Adding `created_at = db.Column(db.DateTime, default=datetime.utcnow)` enables chronological sorting.

7. **Wrong DOM selector in security dashboard**: `loadLiveMonitor()` uses `document.querySelector('#dashboard tbody')` which selects the first `<tbody>` inside the element with `id="dashboard"`. The actual target element has `id="liveMonitorBody"` and is a `<tbody>` directly — the correct selector is `document.getElementById('liveMonitorBody')`.

8. **Dean live monitor limited to 5 records**: `allRequests.slice(-5).reverse()` caps the monitor at the last 5 requests. The fix is to remove the `.slice(-5)` call and show all approved requests.

9. **No auto-refresh on Dean dashboard**: `loadDashboard()` is called once on `DOMContentLoaded`. Adding `setInterval(loadDashboard, 30000)` provides the 30-second auto-refresh.

10. **HOD analytics not department-filtered**: `GET /analytics` returns global counts. The fix adds an optional `?department=<dept>` query parameter to the existing `/analytics` route, which the HOD dashboard passes using the department read from localStorage.


## Correctness Properties

Property 1: Bug Condition — Dynamic Identity and Defined Functions

_For any_ dashboard page load where a valid localStorage session exists (keys: `name`, `role`, `roll_number`, `department`, `token`), the fixed dashboard SHALL read and render the identity values from localStorage rather than hardcoded strings, AND all button `onclick` handlers (`submitReq`, `resetForm`, `loadHistory`, `loadQR`) SHALL be defined functions that execute without a `ReferenceError`.

**Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8, 2.9, 2.10, 2.11, 2.12, 2.13, 2.14, 2.15, 2.16, 2.17, 2.18, 2.19, 2.20, 2.21, 2.22, 2.23, 2.24, 2.25, 2.26**

Property 2: Bug Condition — Backend Routes and Model Completeness

_For any_ API call to `GET /student/profile`, `PUT /dean/reject/<id>`, or `GET /security/stats`, the fixed Flask app SHALL return a valid JSON response with HTTP 200 (or 404 only when the resource genuinely does not exist), AND the `OutpassRequest` model SHALL include a `created_at` timestamp column, AND the Flask app SHALL start successfully even when the `qrcode` package is not installed.

**Validates: Requirements 2.29, 2.31, 2.32, 2.33, 2.30, 2.27, 2.28**

Property 3: Preservation — Existing API Contracts Unchanged

_For any_ API call to an existing route (`POST /apply-outpass`, `GET /student-requests`, `PUT /mentor/approve/<id>`, `PUT /mentor/reject/<id>`, `PUT /parent/approve/<id>`, `PUT /parent/reject/<id>`, `PUT /hod/approve/<id>`, `PUT /hod/reject/<id>`, `PUT /dean/approve/<id>`, `GET /analytics`, `GET /security/verify/<id>`, `POST /register`, `POST /login`), the fixed Flask app SHALL produce the same response structure and status codes as the original app.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10, 3.11, 3.12, 3.13, 3.14, 3.15, 3.16, 3.17, 3.18**


## Fix Implementation

### Changes Required

#### File: `app.py`

**1. Graceful `qrcode` import**

Replace the top-level `import qrcode` with a try/except so the app starts even without the package:

```python
try:
    import qrcode
    QR_AVAILABLE = True
except ImportError:
    QR_AVAILABLE = False
    print("WARNING: qrcode package not installed. QR generation disabled.")
```

Guard the QR generation block inside `dean_approve` with `if QR_AVAILABLE:`.

**2. Add `created_at` to `OutpassRequest`**

Add one column to the model (SQLAlchemy will create it on the next `db.create_all()` for a fresh database; existing databases need a migration or manual `ALTER TABLE`):

```python
from datetime import datetime
# inside OutpassRequest:
created_at = db.Column(db.DateTime, default=datetime.utcnow)
```

Include `created_at` in the serialized output of `student_requests()` and `dean_pending()`.

**3. Create `static/` directory and fix static serving**

Create the `static/qr/` directory in the project root so Flask can serve QR images at `/static/qr/<filename>`. The existing `static_folder='static'` config in `Flask(...)` is already correct — the directory just needs to exist. Add `os.makedirs('static/qr', exist_ok=True)` inside the `if __name__ == '__main__':` block (or at module level).

**4. Add `GET /student/profile`**

```python
@app.route('/student/profile', methods=['GET'])
def student_profile():
    roll = request.args.get('roll_number', '')
    user = User.query.filter_by(role='student').filter(
        User.name != ''
    ).first()  # fallback; ideally use JWT identity
    # Return identity fields; attendance is stored on OutpassRequest
    # Use average attendance from existing requests as a proxy
    reqs = OutpassRequest.query.filter_by(roll_number=roll).all()
    avg_att = round(sum(r.attendance for r in reqs) / len(reqs), 1) if reqs else 75.0
    return jsonify({
        'name': roll,  # replaced by JWT-based lookup in full auth flow
        'roll_number': roll,
        'department': reqs[0].department if reqs else '',
        'attendance': avg_att
    })
```

> Note: A full JWT-authenticated profile endpoint is the ideal end state. For this bugfix, the endpoint accepts `?roll_number=` as a query param (matching how the student dashboard already knows the roll from localStorage) and returns the attendance average computed from existing requests.

**5. Add `PUT /dean/reject/<id>`**

```python
@app.route('/dean/reject/<int:id>', methods=['PUT'])
def dean_reject(id):
    req = db.session.get(OutpassRequest, id)
    if not req:
        return jsonify({'message': 'Request not found'}), 404
    req.dean_status = 'Rejected'
    req.final_status = 'Rejected'
    db.session.commit()
    return jsonify({'message': 'Rejected By Dean'})
```

**6. Add `GET /security/stats`**

```python
@app.route('/security/stats', methods=['GET'])
def security_stats():
    outside = OutpassRequest.query.filter_by(final_status='Approved').count()
    approved = outside  # same set for now
    rejected = OutpassRequest.query.filter_by(final_status='Rejected').count()
    total = OutpassRequest.query.count()
    pending = total - approved - rejected
    return jsonify({
        'outside_count': outside,
        'approved_count': approved,
        'rejected_count': rejected,
        'pending_count': pending
    })
```

**7. Add optional `?department=` filter to `GET /analytics`**

```python
@app.route('/analytics', methods=['GET'])
def analytics():
    dept = request.args.get('department', '')
    query = OutpassRequest.query
    if dept:
        query = query.filter_by(department=dept)
    total = query.count()
    approved = query.filter_by(final_status='Approved').count()
    rejected = query.filter_by(final_status='Rejected').count()
    pending = total - approved - rejected
    return jsonify({
        'total_requests': total,
        'approved_requests': approved,
        'rejected_requests': rejected,
        'pending_requests': pending
    })
```

**8. Add `requirements.txt`**

```
Flask==3.0.3
Flask-SQLAlchemy==3.1.1
Flask-CORS==4.0.1
Flask-JWT-Extended==4.6.0
Werkzeug==3.0.3
qrcode[pil]==7.4.2
Pillow==10.3.0
```


#### File: `student_dashboard.html`

**Session read on load** — replace the three hardcoded constants at the top of the `<script>` block:

```js
// BEFORE
const ROLL = '2021CS01';
const STUDENT_NAME = 'Elakkiya S.';
const DEPT = 'Computer Science';

// AFTER
const ROLL = localStorage.getItem('roll_number') || '';
const STUDENT_NAME = localStorage.getItem('name') || 'Student';
const DEPT = localStorage.getItem('department') || '';
```

Replace every hardcoded identity string in the HTML (top-nav name, welcome heading, roll/dept spans, apply-form readonly inputs) with `id`-targeted DOM writes on `DOMContentLoaded`.

**Fix broken timeline HTML** — the `<div class="time...` tag is truncated mid-attribute in the status tab. Replace with the complete `<div class="timeline">` wrapper that already exists in the `loadStatus()` JS function output (the JS-generated timeline is correct; the static HTML placeholder is the broken one — remove the static placeholder entirely and let `loadStatus()` populate `#statusList`).

**Define `submitReq(btn)`**:

```js
async function submitReq(btn) {
    const reason = document.getElementById('reason').value;
    const destination = document.getElementById('destination').value;
    const exit_time = document.getElementById('exit_time').value;
    const return_time = document.getElementById('return_time').value;
    if (!reason || !destination || !exit_time || !return_time) {
        document.getElementById('formMsg').style.display = 'block';
        document.getElementById('formMsg').innerHTML =
            '<div class="alert alert-warning">Please fill in all required fields.</div>';
        return;
    }
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Submitting...';
    try {
        const res = await fetch(`${API}/apply-outpass`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_name: STUDENT_NAME,
                roll_number: ROLL,
                department: DEPT,
                reason, destination, exit_time, return_time,
                attendance: 75
            })
        });
        const data = await res.json();
        document.getElementById('formMsg').style.display = 'block';
        document.getElementById('formMsg').innerHTML =
            `<div class="alert alert-success">Request #${data.id} submitted successfully!</div>`;
        btn.innerHTML = '<i class="fa-solid fa-check"></i> Submitted';
        setTimeout(() => switchTab('status',
            document.querySelector('.nav-link[onclick*="status"]')), 1500);
    } catch (e) {
        btn.disabled = false;
        btn.innerHTML = 'Submit Request';
        document.getElementById('formMsg').style.display = 'block';
        document.getElementById('formMsg').innerHTML =
            '<div class="alert alert-danger">Error connecting to server.</div>';
    }
}
```

**Define `resetForm()`**:

```js
function resetForm() {
    document.getElementById('reason').value = '';
    document.getElementById('destination').value = '';
    document.getElementById('exit_time').value = '';
    document.getElementById('return_time').value = '';
    document.getElementById('contact').value = '';
    document.getElementById('formMsg').style.display = 'none';
}
```

**Define `loadHistory()`**:

```js
async function loadHistory() {
    const tbody = document.getElementById('historyBody');
    tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">Loading...</td></tr>';
    try {
        const res = await fetch(`${API}/student-requests?roll_number=${ROLL}`);
        const data = await res.json();
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="6" class="text-center text-muted">No history yet.</td></tr>';
            return;
        }
        tbody.innerHTML = data.slice().reverse().map(r => {
            const badge = r.status === 'Approved'
                ? 'bg-success' : r.status === 'Rejected' ? 'bg-danger' : 'bg-warning text-dark';
            return `<tr>
                <td>${r.created_at ? r.created_at.split('T')[0] : '--'}</td>
                <td>${r.reason}</td>
                <td>${r.exit_time || '--'}</td>
                <td>${r.return_time || '--'}</td>
                <td>${r.status === 'Approved' ? '<span class="badge bg-success">Ready</span>' : '--'}</td>
                <td><span class="badge ${badge}">${r.status}</span></td>
            </tr>`;
        }).join('');
    } catch (e) {
        tbody.innerHTML = '<tr><td colspan="6" class="text-center text-danger">Could not load history.</td></tr>';
    }
}
```

**Define `loadQR()`**:

```js
async function loadQR() {
    const container = document.getElementById('qrContent');
    container.innerHTML = '<p class="text-muted text-center">Loading QR pass...</p>';
    try {
        const res = await fetch(`${API}/student-requests?roll_number=${ROLL}`);
        const data = await res.json();
        const approved = data.filter(r => r.status === 'Approved');
        if (approved.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">No approved outpass. Submit a request first.</p>';
            return;
        }
        const latest = approved[approved.length - 1];
        container.innerHTML = `
            <h5 class="text-center mb-3"><i class="fa-solid fa-qrcode text-primary"></i> Your QR Pass</h5>
            <p class="text-center text-muted small">Request #${latest.id} — ${latest.reason}</p>
            <div class="text-center mt-3">
                <img src="${API}/static/qr/qr_${latest.id}.png"
                     alt="QR Code" style="max-width:200px;border-radius:8px;"
                     onerror="this.outerHTML='<p class=\\'text-warning text-center\\'>QR image not yet generated.</p>'">
            </div>`;
    } catch (e) {
        container.innerHTML = '<p class="text-danger text-center">Could not load QR pass.</p>';
    }
}
```

**Dynamic attendance circle** — inside `loadDashboard()`, after fetching student requests, also fetch `/student/profile?roll_number=${ROLL}` and update the circle:

```js
const profileRes = await fetch(`${API}/student/profile?roll_number=${ROLL}`);
const profile = await profileRes.json();
const pct = profile.attendance || 75;
document.getElementById('attendancePct').textContent = pct + '%';
document.querySelector('.circle-wrap').style.background =
    `conic-gradient(var(--success) ${pct}%, rgba(255,255,255,0.1) 0)`;
```

**Dynamic notifications** — replace the three hardcoded `<div class="notif-card">` elements with a `<div id="notifList"></div>` placeholder, and populate it from the student's recent requests on panel open.


#### File: `mentor_dashboard.html`

**Session read on load**:

```js
document.addEventListener('DOMContentLoaded', () => {
    const name = localStorage.getItem('name') || 'Mentor';
    document.querySelector('.profile-avatar').textContent =
        name.split(' ').map(w => w[0]).join('').toUpperCase().slice(0, 2);
    document.querySelector('[style*="font-size: 1rem"]').textContent = name;
    loadPending();
});
```

**Add Rejected stat card** — add a third `<div class="stat-card">` with `id="rejectedCount"` to the `.analytics-grid`, and populate it in `loadPending()`:

```js
document.getElementById('rejectedCount').textContent = analytics.rejected_requests;
```

**"My Students" view** — change the sidebar link from `href="#"` to `onclick="loadMyStudents()"` and define:

```js
async function loadMyStudents() {
    const res = await fetch(`${API}/student-requests`);
    const data = await res.json();
    // render a simple list of unique student names/rolls in the requestsGrid
}
```

#### File: `parent_dashboard.html`

**Dynamic welcome heading** — remove the hardcoded `"Welcome, Parent of John Doe 👋"` string. On `DOMContentLoaded`, read the student name from the first pending request returned by `loadPending()` and set it:

```js
// inside showRequest(), after r is set:
document.querySelector('.welcome-card h1').textContent =
    `Welcome, Parent of ${r.student_name} 👋`;
document.querySelector('.welcome-card p').textContent =
    `${r.department} Dept`;
```

**Remove hardcoded initial data** — replace the static `.details-card` rows (`"Family Medical Emergency"`, `"Hometown"`, `"Oct 24, 05:00 PM"`) with empty placeholder rows. The existing `showRequest()` function already overwrites `.details-card` dynamically — the fix is to start with empty/neutral content so there is no flash of incorrect data before `loadPending()` completes.

**Dynamic timeline** — replace the static hardcoded `<div class="steps">` HTML (which always shows Mentor=completed, Parent=active) with a `<div id="timelineSteps" class="steps"></div>` placeholder. Populate it inside `showRequest()` based on `r.mentor_status`, `r.parent_status`, `r.hod_status`, `r.dean_status`.

#### File: `hod_dashboard.html`

**Session read on load**:

```js
document.addEventListener('DOMContentLoaded', () => {
    const name = localStorage.getItem('name') || 'HOD';
    const dept = localStorage.getItem('department') || 'Computer Science';
    document.querySelector('[style*="font-size:1rem"]').textContent = name;
    document.querySelector('[style*="HOD •"]').textContent = `HOD • ${dept}`;
    loadPending();
});
```

**Department-filtered analytics** — change the analytics fetch in `loadPending()`:

```js
// BEFORE
fetch(`${API}/analytics`)
// AFTER
fetch(`${API}/analytics?department=${encodeURIComponent(dept)}`)
```

#### File: `dean_dashboard.html`

**Session read on load**:

```js
document.addEventListener('DOMContentLoaded', () => {
    const name = localStorage.getItem('name') || 'Dean';
    document.querySelector('[style*="fa-user-tie"]').nextSibling.textContent = ` ${name}`;
    loadDashboard();
    setInterval(loadDashboard, 30000);
});
```

**Show all approved requests** — in `loadDashboard()`, remove `.slice(-5)`:

```js
// BEFORE
const recent = allRequests.slice(-5).reverse();
// AFTER
const recent = allRequests.filter(r => r.status === 'Approved').reverse();
```

**Add Reject button to approval items** — each approval card in `#approvalList` needs a reject button alongside "Grant & Generate QR":

```html
<button onclick="rejectApproval(${r.id})" style="...">
    <i class="fa-solid fa-xmark"></i> Reject
</button>
```

```js
async function rejectApproval(id) {
    await fetch(`${API}/dean/reject/${id}`, { method: 'PUT' });
    setTimeout(loadDashboard, 500);
}
```

#### File: `security_dashboard.html`

**Fix `#liveMonitorBody` selector** — in `loadLiveMonitor()`:

```js
// BEFORE
const tbody = document.querySelector('#dashboard tbody');
// AFTER
const tbody = document.getElementById('liveMonitorBody');
```

**Update stat cards from `/security/stats`** — add to `loadLiveMonitor()`:

```js
const statsRes = await fetch(`${API}/security/stats`);
const stats = await statsRes.json();
document.getElementById('outsideCount').textContent = stats.outside_count;
document.getElementById('approvedCount').textContent = stats.approved_count;
document.getElementById('rejectedCount').textContent = stats.rejected_count;
document.getElementById('pendingCount').textContent = stats.pending_count;
```

**Live clock** — add to `DOMContentLoaded`:

```js
function updateClock() {
    const now = new Date();
    document.querySelector('.text-muted.small').innerHTML =
        `<i class="fa-regular fa-clock"></i> ${now.toLocaleString()}`;
}
setInterval(updateClock, 1000);
updateClock();
```

**Officer name from localStorage**:

```js
const officerName = localStorage.getItem('name') || 'Security Officer';
document.querySelector('.small.fw-bold').textContent = officerName;
```

**Dynamic charts** — replace the hardcoded `data` arrays in the three Chart.js initializations with values fetched from `GET /analytics` and `GET /security/stats`. For the exit timing chart, use the count of approved requests as a proxy until a dedicated time-series endpoint is added.

**Dynamic security logs** — replace the three hardcoded `<tr>` rows in the logs tab with a `<tbody id="logsBody">` populated from `GET /student-requests` (showing scan/verification events derived from request status changes).


## Testing Strategy

### Validation Approach

The testing strategy follows a two-phase approach: first, surface counterexamples that demonstrate each bug on the unfixed code to confirm the root cause analysis; then verify the fix works correctly and preserves all existing behavior.

Because the project uses plain HTML/JS with no frontend framework, frontend tests use a browser-based test runner (e.g., a simple `test.html` page with assertions, or Playwright for end-to-end). Backend tests use Python's `unittest` with Flask's test client.

### Exploratory Bug Condition Checking

**Goal**: Surface counterexamples that demonstrate each bug BEFORE implementing the fix. Confirm or refute the root cause analysis.

**Test Plan**: Run the Flask app on unfixed code, open each dashboard, and observe failures. For JS function bugs, open the browser console and trigger each button. For API bugs, use `curl` or the browser network tab.

**Test Cases**:

1. **Missing JS functions** (will fail on unfixed code):
   - Open `student_dashboard.html`, click "Submit Request" → expect `ReferenceError: submitReq is not defined` in console.
   - Click "Reset Form" → expect `ReferenceError: resetForm is not defined`.
   - Click "Leave History" tab → expect `ReferenceError: loadHistory is not defined`.
   - Click "QR Pass" tab → expect `ReferenceError: loadQR is not defined`.

2. **Hardcoded identity** (will fail on unfixed code):
   - Log in as a user with name "Test User", then open `/student` → expect to see "Elakkiya S." instead of "Test User".
   - Open `/mentor` → expect to see "Prof. Jane Doe" regardless of logged-in user.

3. **Missing API routes** (will fail on unfixed code):
   - `curl http://127.0.0.1:5000/student/profile?roll_number=2021CS01` → expect HTTP 404.
   - `curl -X PUT http://127.0.0.1:5000/dean/reject/1` → expect HTTP 404.
   - `curl http://127.0.0.1:5000/security/stats` → expect HTTP 404.

4. **Wrong DOM selector** (will fail on unfixed code):
   - Open `/security`, wait for `loadLiveMonitor()` → expect live monitor table to remain empty even when approved requests exist in the database.

5. **Flask startup crash** (will fail on unfixed code if qrcode not installed):
   - Uninstall qrcode: `pip uninstall qrcode` → start Flask → expect `ImportError` crash.

**Expected Counterexamples**:
- Browser console shows `ReferenceError` for all four missing student dashboard functions.
- Network tab shows 404 for the three missing API routes.
- Security live monitor table body is never populated despite approved records existing.
- Flask process exits immediately on startup without qrcode installed.

### Fix Checking

**Goal**: Verify that for all inputs where the bug condition holds, the fixed code produces the expected behavior.

**Pseudocode:**

```
FOR ALL input WHERE isBugCondition(input) DO
  result := fixedSystem(input)
  ASSERT expectedBehavior(result)
END FOR
```

**Test Cases**:

1. **JS functions defined**: After fix, open student dashboard → `typeof submitReq === 'function'`, `typeof resetForm === 'function'`, `typeof loadHistory === 'function'`, `typeof loadQR === 'function'`.
2. **submitReq posts correctly**: Fill form, click Submit → network request to `POST /apply-outpass` with correct body, success message shown, tab switches to status.
3. **resetForm clears fields**: Fill form, click Reset → all fields empty.
4. **loadHistory populates table**: Navigate to Leave History tab → `#historyBody` contains rows from the database (not "Loading history...").
5. **loadQR shows image**: Navigate to QR Pass tab with an approved request → QR image displayed.
6. **Identity from localStorage**: Set `localStorage.setItem('name', 'Priya R.')` in console, reload student dashboard → welcome heading shows "Priya R.", not "Elakkiya S.".
7. **`GET /student/profile` returns 200**: `curl http://127.0.0.1:5000/student/profile?roll_number=2021CS01` → JSON with `name`, `roll_number`, `department`, `attendance`.
8. **`PUT /dean/reject/<id>` returns 200**: `curl -X PUT http://127.0.0.1:5000/dean/reject/1` → `{"message": "Rejected By Dean"}`, database record has `dean_status='Rejected'`.
9. **`GET /security/stats` returns 200**: Returns JSON with `outside_count`, `approved_count`, `rejected_count`, `pending_count`.
10. **Security live monitor populates**: After fix, `loadLiveMonitor()` correctly targets `#liveMonitorBody` and rows appear.
11. **Flask starts without qrcode**: Uninstall qrcode, start Flask → app starts, warning logged, all non-QR routes work.
12. **`created_at` stored**: Submit a new outpass → `GET /student-requests` response includes `created_at` field.
13. **HOD analytics filtered**: Set `localStorage.setItem('department', 'CS')`, open HOD dashboard → analytics call includes `?department=CS`.
14. **Dean shows all approved**: Open Dean dashboard with >5 approved requests → all appear in live monitor, not just 5.
15. **Dean auto-refresh**: Open Dean dashboard, wait 30 seconds → `loadDashboard()` called again (verify via network tab).

### Preservation Checking

**Goal**: Verify that for all inputs where the bug condition does NOT hold, the fixed system produces the same result as the original system.

**Pseudocode:**

```
FOR ALL input WHERE NOT isBugCondition(input) DO
  ASSERT originalSystem(input) = fixedSystem(input)
END FOR
```

**Testing Approach**: Property-based testing is recommended for the backend API preservation checks because it generates many request combinations automatically and catches edge cases (empty databases, concurrent requests, boundary attendance values).

**Test Cases**:

1. **Mentor approve/reject preserved**: `PUT /mentor/approve/1` and `PUT /mentor/reject/1` return the same JSON and produce the same database state before and after the fix.
2. **Parent approve/reject preserved**: Same verification for parent routes.
3. **HOD approve/reject preserved**: Same verification for HOD routes. Specifically verify `PUT /hod/reject/<id>` still sets both `hod_status='Rejected'` AND `final_status='Rejected'`.
4. **Dean approve preserved**: `PUT /dean/approve/<id>` still sets `dean_status='Approved'`, `final_status='Approved'`, generates QR, returns `qr_file` path.
5. **`GET /analytics` without dept param preserved**: Calling `GET /analytics` (no query param) returns the same global counts as before.
6. **`POST /apply-outpass` preserved**: Same request body produces same response structure (`{"message": ..., "id": ...}`).
7. **`GET /student-requests` preserved**: Same response structure and filtering behavior.
8. **`POST /login` preserved**: Same response structure (`token`, `role`, `name`).
9. **`GET /security/verify/<id>` preserved**: VALID/INVALID logic unchanged.
10. **Parent `confirmAction()` preserved**: Approve/reject a request via the parent dashboard UI → request removed from queue, "Next Pending Request" button appears if more remain.
11. **Mentor attendance risk colors preserved**: HIGH RISK (<75%), WARNING (<85%), SAFE (≥85%) color logic unchanged in mentor dashboard cards.

### Unit Tests

- Test `dean_reject()` route: valid ID returns 200 with correct message; invalid ID returns 404.
- Test `security_stats()` route: returns correct counts matching database state.
- Test `student_profile()` route: returns correct attendance average for a roll number with known requests.
- Test `analytics()` route with `?department=CS`: returns only CS department counts.
- Test `analytics()` route without department param: returns global counts (regression).
- Test `OutpassRequest.created_at` default: new record has a non-null `created_at` timestamp.
- Test `submitReq()` JS function: mock `fetch`, verify correct POST body constructed from form fields and localStorage values.
- Test `resetForm()` JS function: verify all form fields are empty after call.
- Test `loadHistory()` JS function: mock fetch response, verify `#historyBody` rows match response data.
- Test `loadQR()` JS function: mock fetch with approved request, verify QR image `src` is set correctly.

### Property-Based Tests

- **Property 1 (Fix)**: For any `roll_number` string, `GET /student/profile?roll_number=<roll>` returns a JSON object with keys `name`, `roll_number`, `department`, `attendance` where `attendance` is a float between 0 and 100.
- **Property 2 (Fix)**: For any valid outpass request ID with `hod_status='Approved'` and `dean_status='Pending'`, `PUT /dean/reject/<id>` sets `dean_status='Rejected'` AND `final_status='Rejected'` (both fields, not just one).
- **Property 3 (Preservation)**: For any combination of `(total, approved, rejected)` counts in the database, `GET /analytics` (no dept param) returns `pending_requests = total - approved - rejected` (the arithmetic invariant is preserved after adding the dept filter).
- **Property 4 (Preservation)**: For any outpass request ID, calling `PUT /mentor/approve/<id>` followed by `GET /student-requests?roll_number=<roll>` returns a record where `mentor_status='Approved'` — the approval chain logic is unchanged.
- **Property 5 (Preservation)**: For any attendance value `a` in [0, 100], the mentor dashboard risk classification is: `a < 75 → HIGH RISK`, `75 ≤ a < 85 → WARNING`, `a ≥ 85 → SAFE` — unchanged by the fix.

### Integration Tests

- **Full student flow**: Register student → login → localStorage populated → open student dashboard → identity shown correctly → submit outpass → history tab shows new record → (after approval chain) QR tab shows QR image.
- **Full approval chain**: Student submits → mentor approves → parent approves → HOD approves → dean approves → `final_status='Approved'` → security stats `outside_count` increments by 1.
- **Dean reject flow**: Student submits → approval chain reaches dean → dean rejects via new `PUT /dean/reject/<id>` → `final_status='Rejected'` → request disappears from dean pending list.
- **Security dashboard end-to-end**: Open security dashboard → stat cards populated from `/security/stats` → live monitor table populated with approved requests → clock ticks every second → officer name from localStorage.
- **HOD department filter**: Two students from different departments submit requests → HOD with `department=CS` in localStorage sees only CS counts in analytics cards.
- **Flask startup resilience**: Remove qrcode from environment → start Flask → all routes except QR generation respond correctly → warning message in logs.

