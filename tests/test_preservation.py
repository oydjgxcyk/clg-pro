"""
Preservation Property Tests — Task 2
=====================================
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 3.10,
             3.11, 3.12, 3.13, 3.14, 3.15, 3.16, 3.17, 3.18**

Property 2: Preservation — Existing API Contracts and UI Interactions Unchanged

These tests observe the UNFIXED code's existing working routes and assert that
their response shapes hold. They are EXPECTED TO PASS on unfixed code, establishing
the baseline behavior that must be preserved after the bugfix is applied.

Methodology: observation-first — each test encodes what the unfixed app already
returns, so any regression introduced by the fix will cause a test failure.
"""

import os
import sys
import json
import unittest

# ---------------------------------------------------------------------------
# Project root on sys.path so we can import app.py
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Module-level shared state (populated in setUpClass)
# ---------------------------------------------------------------------------

_client = None
_import_error = None
_shared_request_id = None   # id of the outpass created in setUpClass
_shared_roll = 'TEST_ROLL_001'
_shared_email = 'preservation_test_user@example.com'
_shared_password = 'TestPass123!'
_shared_name = 'Preservation Tester'


# ---------------------------------------------------------------------------
# Base class — provides client and shared request id to all test cases
# ---------------------------------------------------------------------------

class _BasePreservation(unittest.TestCase):
    """Mixin that provides the shared Flask test client and request id."""

    @classmethod
    def setUpClass(cls):
        """
        Import app, create tables, register a test user, submit an outpass,
        and run the full approval chain so every approval/rejection route has
        a real record to act on.
        """
        global _client, _import_error, _shared_request_id

        if _client is not None:
            # Already initialised by a previous test class in this run.
            cls.client = _client
            cls.request_id = _shared_request_id
            cls.import_error = _import_error
            return

        try:
            import app as flask_app
            with flask_app.app.app_context():
                flask_app.db.create_all()

                # Clean up any leftover test data from previous runs.
                flask_app.User.query.filter_by(email=_shared_email).delete()
                flask_app.db.session.commit()

            _client = flask_app.app.test_client()
            _import_error = None
        except Exception as exc:
            _client = None
            _import_error = exc
            cls.client = None
            cls.request_id = None
            cls.import_error = exc
            return

        cls.client = _client
        cls.import_error = None

        # --- Register a test user ---
        reg_resp = cls.client.post(
            '/register',
            data=json.dumps({
                'name': _shared_name,
                'email': _shared_email,
                'password': _shared_password,
                'role': 'student',
                'department': 'Computer Science'
            }),
            content_type='application/json'
        )
        # Accept 200 (new) or 409 (already exists from a previous run).
        assert reg_resp.status_code in (200, 409), (
            f"Register returned unexpected status {reg_resp.status_code}"
        )

        # --- Submit an outpass request ---
        apply_resp = cls.client.post(
            '/apply-outpass',
            data=json.dumps({
                'student_name': _shared_name,
                'roll_number': _shared_roll,
                'department': 'Computer Science',
                'reason': 'Medical appointment',
                'destination': 'City Hospital',
                'exit_time': '2024-01-15 10:00',
                'return_time': '2024-01-15 18:00',
                'attendance': 85.0
            }),
            content_type='application/json'
        )
        assert apply_resp.status_code == 200, (
            f"apply-outpass returned {apply_resp.status_code}"
        )
        apply_data = json.loads(apply_resp.data)
        _shared_request_id = apply_data['id']
        cls.request_id = _shared_request_id

    def _require_client(self):
        if self.client is None:
            self.fail(
                f"Could not import app.py — import raised: {self.import_error}"
            )


# ---------------------------------------------------------------------------
# Test 1 — POST /apply-outpass returns {"id": <int>, "message": ...} HTTP 200
# ---------------------------------------------------------------------------

class TestApplyOutpass(_BasePreservation):
    """
    Requirement 3.9 — POST /apply-outpass continues to create a new
    OutpassRequest and return the new request's id.
    """

    def test_apply_outpass_returns_200(self):
        """POST /apply-outpass returns HTTP 200."""
        self._require_client()
        resp = self.client.post(
            '/apply-outpass',
            data=json.dumps({
                'student_name': 'Another Student',
                'roll_number': 'ROLL_002',
                'department': 'ECE',
                'reason': 'Family visit',
                'destination': 'Home',
                'exit_time': '2024-02-01 09:00',
                'return_time': '2024-02-01 20:00',
                'attendance': 78.0
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200,
            f"POST /apply-outpass returned {resp.status_code}, expected 200")

    def test_apply_outpass_returns_id_int(self):
        """POST /apply-outpass response body contains 'id' as an integer."""
        self._require_client()
        resp = self.client.post(
            '/apply-outpass',
            data=json.dumps({
                'student_name': 'Third Student',
                'roll_number': 'ROLL_003',
                'department': 'Mech',
                'reason': 'Sports event',
                'destination': 'Stadium',
                'exit_time': '2024-03-01 08:00',
                'return_time': '2024-03-01 22:00',
                'attendance': 90.0
            }),
            content_type='application/json'
        )
        data = json.loads(resp.data)
        self.assertIn('id', data,
            "Response from POST /apply-outpass must contain 'id' key")
        self.assertIsInstance(data['id'], int,
            f"'id' must be an integer, got {type(data['id'])}")

    def test_apply_outpass_returns_message(self):
        """POST /apply-outpass response body contains a 'message' key."""
        self._require_client()
        resp = self.client.post(
            '/apply-outpass',
            data=json.dumps({
                'student_name': 'Fourth Student',
                'roll_number': 'ROLL_004',
                'department': 'Civil',
                'reason': 'Medical',
                'destination': 'Hospital',
                'exit_time': '2024-04-01 10:00',
                'return_time': '2024-04-01 17:00',
                'attendance': 82.0
            }),
            content_type='application/json'
        )
        data = json.loads(resp.data)
        self.assertIn('message', data,
            "Response from POST /apply-outpass must contain 'message' key")


# ---------------------------------------------------------------------------
# Test 2 — PUT /mentor/approve/<id> → {"message": "Approved By Mentor"} 200
# ---------------------------------------------------------------------------

class TestMentorApprove(_BasePreservation):
    """
    Requirement 3.1 — PUT /mentor/approve/<id> continues to update
    mentor_status and return the existing success response format.
    """

    def test_mentor_approve_returns_200(self):
        """PUT /mentor/approve/<id> returns HTTP 200."""
        self._require_client()
        resp = self.client.put(f'/mentor/approve/{self.request_id}')
        self.assertEqual(resp.status_code, 200,
            f"PUT /mentor/approve/{self.request_id} returned {resp.status_code}")

    def test_mentor_approve_returns_correct_message(self):
        """PUT /mentor/approve/<id> returns {"message": "Approved By Mentor"}."""
        self._require_client()
        resp = self.client.put(f'/mentor/approve/{self.request_id}')
        data = json.loads(resp.data)
        self.assertEqual(data.get('message'), 'Approved By Mentor',
            f"Expected 'Approved By Mentor', got: {data}")

    def test_mentor_approve_404_for_missing_id(self):
        """PUT /mentor/approve/<nonexistent_id> returns HTTP 404."""
        self._require_client()
        resp = self.client.put('/mentor/approve/999999')
        self.assertEqual(resp.status_code, 404,
            f"Expected 404 for missing id, got {resp.status_code}")


# ---------------------------------------------------------------------------
# Test 3 — PUT /mentor/reject/<id> → {"message": "Rejected By Mentor"} 200
# ---------------------------------------------------------------------------

class TestMentorReject(_BasePreservation):
    """
    Requirement 3.1 — PUT /mentor/reject/<id> continues to update
    mentor_status and return the existing success response format.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a fresh request dedicated to rejection so we don't conflict
        # with the approval tests.
        if cls.client is None:
            return
        resp = cls.client.post(
            '/apply-outpass',
            data=json.dumps({
                'student_name': 'Reject Test Student',
                'roll_number': 'ROLL_REJECT_MENTOR',
                'department': 'CS',
                'reason': 'Test rejection',
                'destination': 'Nowhere',
                'exit_time': '2024-05-01 09:00',
                'return_time': '2024-05-01 18:00',
                'attendance': 70.0
            }),
            content_type='application/json'
        )
        cls.reject_id = json.loads(resp.data)['id']

    def test_mentor_reject_returns_200(self):
        """PUT /mentor/reject/<id> returns HTTP 200."""
        self._require_client()
        resp = self.client.put(f'/mentor/reject/{self.reject_id}')
        self.assertEqual(resp.status_code, 200,
            f"PUT /mentor/reject/{self.reject_id} returned {resp.status_code}")

    def test_mentor_reject_returns_correct_message(self):
        """PUT /mentor/reject/<id> returns {"message": "Rejected By Mentor"}."""
        self._require_client()
        resp = self.client.put(f'/mentor/reject/{self.reject_id}')
        data = json.loads(resp.data)
        self.assertEqual(data.get('message'), 'Rejected By Mentor',
            f"Expected 'Rejected By Mentor', got: {data}")


# ---------------------------------------------------------------------------
# Test 4 — PUT /parent/approve/<id> → {"message": "Approved By Parent"} 200
# ---------------------------------------------------------------------------

class TestParentApprove(_BasePreservation):
    """
    Requirement 3.2 — PUT /parent/approve/<id> continues to update
    parent_status and return the existing success response format.
    """

    def test_parent_approve_returns_200(self):
        """PUT /parent/approve/<id> returns HTTP 200."""
        self._require_client()
        resp = self.client.put(f'/parent/approve/{self.request_id}')
        self.assertEqual(resp.status_code, 200,
            f"PUT /parent/approve/{self.request_id} returned {resp.status_code}")

    def test_parent_approve_returns_correct_message(self):
        """PUT /parent/approve/<id> returns {"message": "Approved By Parent"}."""
        self._require_client()
        resp = self.client.put(f'/parent/approve/{self.request_id}')
        data = json.loads(resp.data)
        self.assertEqual(data.get('message'), 'Approved By Parent',
            f"Expected 'Approved By Parent', got: {data}")

    def test_parent_approve_404_for_missing_id(self):
        """PUT /parent/approve/<nonexistent_id> returns HTTP 404."""
        self._require_client()
        resp = self.client.put('/parent/approve/999999')
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# Test 5 — PUT /parent/reject/<id> → {"message": "Rejected By Parent"} 200
# ---------------------------------------------------------------------------

class TestParentReject(_BasePreservation):
    """
    Requirement 3.2 — PUT /parent/reject/<id> continues to update
    parent_status and return the existing success response format.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.client is None:
            return
        resp = cls.client.post(
            '/apply-outpass',
            data=json.dumps({
                'student_name': 'Reject Parent Test',
                'roll_number': 'ROLL_REJECT_PARENT',
                'department': 'CS',
                'reason': 'Test parent rejection',
                'destination': 'Nowhere',
                'exit_time': '2024-06-01 09:00',
                'return_time': '2024-06-01 18:00',
                'attendance': 72.0
            }),
            content_type='application/json'
        )
        cls.reject_id = json.loads(resp.data)['id']

    def test_parent_reject_returns_200(self):
        """PUT /parent/reject/<id> returns HTTP 200."""
        self._require_client()
        resp = self.client.put(f'/parent/reject/{self.reject_id}')
        self.assertEqual(resp.status_code, 200,
            f"PUT /parent/reject/{self.reject_id} returned {resp.status_code}")

    def test_parent_reject_returns_correct_message(self):
        """PUT /parent/reject/<id> returns {"message": "Rejected By Parent"}."""
        self._require_client()
        resp = self.client.put(f'/parent/reject/{self.reject_id}')
        data = json.loads(resp.data)
        self.assertEqual(data.get('message'), 'Rejected By Parent',
            f"Expected 'Rejected By Parent', got: {data}")


# ---------------------------------------------------------------------------
# Test 6 — PUT /hod/approve/<id> → {"message": "Approved By HOD"} 200
# ---------------------------------------------------------------------------

class TestHodApprove(_BasePreservation):
    """
    Requirement 3.3 — PUT /hod/approve/<id> continues to update
    hod_status and return the existing success response format.
    """

    def test_hod_approve_returns_200(self):
        """PUT /hod/approve/<id> returns HTTP 200."""
        self._require_client()
        resp = self.client.put(f'/hod/approve/{self.request_id}')
        self.assertEqual(resp.status_code, 200,
            f"PUT /hod/approve/{self.request_id} returned {resp.status_code}")

    def test_hod_approve_returns_correct_message(self):
        """PUT /hod/approve/<id> returns {"message": "Approved By HOD"}."""
        self._require_client()
        resp = self.client.put(f'/hod/approve/{self.request_id}')
        data = json.loads(resp.data)
        self.assertEqual(data.get('message'), 'Approved By HOD',
            f"Expected 'Approved By HOD', got: {data}")

    def test_hod_approve_404_for_missing_id(self):
        """PUT /hod/approve/<nonexistent_id> returns HTTP 404."""
        self._require_client()
        resp = self.client.put('/hod/approve/999999')
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# Test 7 — PUT /hod/reject/<id> → sets hod_status=Rejected AND
#           final_status=Rejected, HTTP 200  (Requirement 3.16)
# ---------------------------------------------------------------------------

class TestHodReject(_BasePreservation):
    """
    Requirement 3.3 / 3.16 — PUT /hod/reject/<id> sets both hod_status and
    final_status to 'Rejected' and returns the existing success response.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.client is None:
            return
        resp = cls.client.post(
            '/apply-outpass',
            data=json.dumps({
                'student_name': 'HOD Reject Test',
                'roll_number': 'ROLL_REJECT_HOD',
                'department': 'CS',
                'reason': 'Test HOD rejection',
                'destination': 'Nowhere',
                'exit_time': '2024-07-01 09:00',
                'return_time': '2024-07-01 18:00',
                'attendance': 68.0
            }),
            content_type='application/json'
        )
        cls.reject_id = json.loads(resp.data)['id']

    def test_hod_reject_returns_200(self):
        """PUT /hod/reject/<id> returns HTTP 200."""
        self._require_client()
        resp = self.client.put(f'/hod/reject/{self.reject_id}')
        self.assertEqual(resp.status_code, 200,
            f"PUT /hod/reject/{self.reject_id} returned {resp.status_code}")

    def test_hod_reject_returns_correct_message(self):
        """PUT /hod/reject/<id> returns {"message": "Rejected By HOD"}."""
        self._require_client()
        resp = self.client.put(f'/hod/reject/{self.reject_id}')
        data = json.loads(resp.data)
        self.assertEqual(data.get('message'), 'Rejected By HOD',
            f"Expected 'Rejected By HOD', got: {data}")

    def test_hod_reject_sets_final_status_rejected(self):
        """PUT /hod/reject/<id> sets final_status to 'Rejected' in the DB."""
        self._require_client()
        # Ensure the rejection has been applied (idempotent call).
        self.client.put(f'/hod/reject/{self.reject_id}')
        # Verify via GET /student-requests.
        resp = self.client.get(
            f'/student-requests?roll_number=ROLL_REJECT_HOD'
        )
        records = json.loads(resp.data)
        matching = [r for r in records if r['id'] == self.reject_id]
        self.assertTrue(matching,
            "Could not find the rejected request in /student-requests")
        self.assertEqual(matching[0]['status'], 'Rejected',
            f"final_status should be 'Rejected', got: {matching[0]['status']}")


# ---------------------------------------------------------------------------
# Test 8 — PUT /dean/approve/<id> → sets final_status=Approved,
#           returns qr_file key, HTTP 200  (Requirement 3.4)
# ---------------------------------------------------------------------------

class TestDeanApprove(_BasePreservation):
    """
    Requirement 3.4 — PUT /dean/approve/<id> continues to set
    dean_status='Approved', final_status='Approved', generate a QR code,
    and return the qr_file path in the response.
    """

    def test_dean_approve_returns_200(self):
        """PUT /dean/approve/<id> returns HTTP 200."""
        self._require_client()
        resp = self.client.put(f'/dean/approve/{self.request_id}')
        self.assertEqual(resp.status_code, 200,
            f"PUT /dean/approve/{self.request_id} returned {resp.status_code}")

    def test_dean_approve_returns_qr_file_key(self):
        """PUT /dean/approve/<id> response contains 'qr_file' key."""
        self._require_client()
        resp = self.client.put(f'/dean/approve/{self.request_id}')
        data = json.loads(resp.data)
        self.assertIn('qr_file', data,
            f"Response from PUT /dean/approve must contain 'qr_file' key. Got: {data}")

    def test_dean_approve_sets_final_status_approved(self):
        """PUT /dean/approve/<id> sets final_status to 'Approved' in the DB."""
        self._require_client()
        self.client.put(f'/dean/approve/{self.request_id}')
        resp = self.client.get(
            f'/student-requests?roll_number={_shared_roll}'
        )
        records = json.loads(resp.data)
        matching = [r for r in records if r['id'] == self.request_id]
        self.assertTrue(matching,
            "Could not find the approved request in /student-requests")
        self.assertEqual(matching[0]['status'], 'Approved',
            f"final_status should be 'Approved', got: {matching[0]['status']}")

    def test_dean_approve_404_for_missing_id(self):
        """PUT /dean/approve/<nonexistent_id> returns HTTP 404."""
        self._require_client()
        resp = self.client.put('/dean/approve/999999')
        self.assertEqual(resp.status_code, 404)


# ---------------------------------------------------------------------------
# Test 9 — GET /student-requests?roll_number=X → array filtered by roll
#           (Requirement 3.10)
# ---------------------------------------------------------------------------

class TestStudentRequests(_BasePreservation):
    """
    Requirement 3.10 — GET /student-requests with roll_number param returns
    only that student's requests; without param returns all requests.
    """

    def test_student_requests_returns_array(self):
        """GET /student-requests returns a JSON array."""
        self._require_client()
        resp = self.client.get('/student-requests')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIsInstance(data, list,
            f"GET /student-requests should return a list, got {type(data)}")

    def test_student_requests_filtered_by_roll(self):
        """GET /student-requests?roll_number=X returns only records for that roll."""
        self._require_client()
        resp = self.client.get(
            f'/student-requests?roll_number={_shared_roll}'
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIsInstance(data, list)
        for record in data:
            self.assertEqual(record['roll_number'], _shared_roll,
                f"Record roll_number '{record['roll_number']}' != '{_shared_roll}'")

    def test_student_requests_unknown_roll_returns_empty_array(self):
        """GET /student-requests?roll_number=NONEXISTENT returns empty array."""
        self._require_client()
        resp = self.client.get('/student-requests?roll_number=NONEXISTENT_ROLL_XYZ')
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data, [],
            f"Expected empty list for unknown roll, got: {data}")

    def test_student_requests_record_has_expected_fields(self):
        """Each record in GET /student-requests has the expected fields."""
        self._require_client()
        resp = self.client.get(
            f'/student-requests?roll_number={_shared_roll}'
        )
        data = json.loads(resp.data)
        self.assertTrue(len(data) > 0, "Expected at least one record")
        record = data[0]
        for field in ('id', 'student_name', 'roll_number', 'reason',
                      'destination', 'exit_time', 'return_time',
                      'mentor_status', 'parent_status', 'hod_status',
                      'dean_status', 'status'):
            self.assertIn(field, record,
                f"Field '{field}' missing from /student-requests record")


# ---------------------------------------------------------------------------
# Test 10 — GET /analytics → returns the four required keys (Requirement 3.11)
# ---------------------------------------------------------------------------

class TestAnalytics(_BasePreservation):
    """
    Requirement 3.11 — GET /analytics continues to return total_requests,
    approved_requests, rejected_requests, and pending_requests counts.
    """

    def test_analytics_returns_200(self):
        """GET /analytics returns HTTP 200."""
        self._require_client()
        resp = self.client.get('/analytics')
        self.assertEqual(resp.status_code, 200,
            f"GET /analytics returned {resp.status_code}")

    def test_analytics_has_total_requests(self):
        """GET /analytics response contains 'total_requests' as an integer."""
        self._require_client()
        data = json.loads(self.client.get('/analytics').data)
        self.assertIn('total_requests', data)
        self.assertIsInstance(data['total_requests'], int)

    def test_analytics_has_approved_requests(self):
        """GET /analytics response contains 'approved_requests' as an integer."""
        self._require_client()
        data = json.loads(self.client.get('/analytics').data)
        self.assertIn('approved_requests', data)
        self.assertIsInstance(data['approved_requests'], int)

    def test_analytics_has_rejected_requests(self):
        """GET /analytics response contains 'rejected_requests' as an integer."""
        self._require_client()
        data = json.loads(self.client.get('/analytics').data)
        self.assertIn('rejected_requests', data)
        self.assertIsInstance(data['rejected_requests'], int)

    def test_analytics_has_pending_requests(self):
        """GET /analytics response contains 'pending_requests' as an integer."""
        self._require_client()
        data = json.loads(self.client.get('/analytics').data)
        self.assertIn('pending_requests', data)
        self.assertIsInstance(data['pending_requests'], int)

    def test_analytics_counts_are_consistent(self):
        """approved + rejected + pending == total in GET /analytics."""
        self._require_client()
        data = json.loads(self.client.get('/analytics').data)
        total = data['total_requests']
        computed = (data['approved_requests']
                    + data['rejected_requests']
                    + data['pending_requests'])
        self.assertEqual(total, computed,
            f"total_requests ({total}) != approved+rejected+pending ({computed})")


# ---------------------------------------------------------------------------
# Test 11 — GET /security/verify/<id> for approved request → VALID + fields
#            (Requirement 3.12)
# ---------------------------------------------------------------------------

class TestSecurityVerify(_BasePreservation):
    """
    Requirement 3.12 — GET /security/verify/<id> for a request with
    final_status='Approved' returns {"status": "VALID"} with student details.
    """

    def test_verify_approved_returns_valid(self):
        """GET /security/verify/<approved_id> returns {"status": "VALID"}."""
        self._require_client()
        # Ensure the shared request is approved (dean approve is idempotent).
        self.client.put(f'/dean/approve/{self.request_id}')
        resp = self.client.get(f'/security/verify/{self.request_id}')
        self.assertEqual(resp.status_code, 200,
            f"GET /security/verify/{self.request_id} returned {resp.status_code}")
        data = json.loads(resp.data)
        self.assertEqual(data.get('status'), 'VALID',
            f"Expected status='VALID', got: {data}")

    def test_verify_approved_has_student_fields(self):
        """GET /security/verify/<approved_id> includes student detail fields."""
        self._require_client()
        self.client.put(f'/dean/approve/{self.request_id}')
        data = json.loads(
            self.client.get(f'/security/verify/{self.request_id}').data
        )
        for field in ('student_name', 'roll_number', 'destination',
                      'exit_time', 'return_time'):
            self.assertIn(field, data,
                f"Field '{field}' missing from /security/verify response")

    def test_verify_unapproved_returns_invalid(self):
        """GET /security/verify/<unapproved_id> returns {"status": "INVALID"}."""
        self._require_client()
        # Create a fresh request that is NOT approved.
        resp = self.client.post(
            '/apply-outpass',
            data=json.dumps({
                'student_name': 'Unverified Student',
                'roll_number': 'ROLL_UNVERIFIED',
                'department': 'CS',
                'reason': 'Test',
                'destination': 'Test',
                'exit_time': '2024-08-01 09:00',
                'return_time': '2024-08-01 18:00',
                'attendance': 80.0
            }),
            content_type='application/json'
        )
        new_id = json.loads(resp.data)['id']
        verify_resp = self.client.get(f'/security/verify/{new_id}')
        data = json.loads(verify_resp.data)
        self.assertEqual(data.get('status'), 'INVALID',
            f"Expected status='INVALID' for unapproved request, got: {data}")


# ---------------------------------------------------------------------------
# Test 12 — POST /register: new email → 200; duplicate email → 409
#            (Requirement 3.13)
# ---------------------------------------------------------------------------

class TestRegister(_BasePreservation):
    """
    Requirement 3.13 — POST /register with a new email creates the user (200);
    duplicate emails return 409.
    """

    _unique_counter = 0

    @classmethod
    def _unique_email(cls):
        cls._unique_counter += 1
        return f'reg_test_{cls._unique_counter}_preservation@example.com'

    def test_register_new_email_returns_200(self):
        """POST /register with a new email returns HTTP 200."""
        self._require_client()
        resp = self.client.post(
            '/register',
            data=json.dumps({
                'name': 'New User',
                'email': self._unique_email(),
                'password': 'Password123!',
                'role': 'student',
                'department': 'CS'
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200,
            f"POST /register with new email returned {resp.status_code}")

    def test_register_duplicate_email_returns_409(self):
        """POST /register with a duplicate email returns HTTP 409."""
        self._require_client()
        email = self._unique_email()
        # First registration — should succeed.
        self.client.post(
            '/register',
            data=json.dumps({
                'name': 'Dup User',
                'email': email,
                'password': 'Password123!',
                'role': 'student',
                'department': 'CS'
            }),
            content_type='application/json'
        )
        # Second registration with same email — should return 409.
        resp = self.client.post(
            '/register',
            data=json.dumps({
                'name': 'Dup User Again',
                'email': email,
                'password': 'AnotherPass!',
                'role': 'student',
                'department': 'CS'
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 409,
            f"POST /register with duplicate email returned {resp.status_code}, expected 409")

    def test_register_response_has_message(self):
        """POST /register response body contains a 'message' key."""
        self._require_client()
        resp = self.client.post(
            '/register',
            data=json.dumps({
                'name': 'Msg Test User',
                'email': self._unique_email(),
                'password': 'Password123!',
                'role': 'mentor',
                'department': 'CS'
            }),
            content_type='application/json'
        )
        data = json.loads(resp.data)
        self.assertIn('message', data,
            f"POST /register response must contain 'message' key. Got: {data}")


# ---------------------------------------------------------------------------
# Test 13 — POST /login: valid credentials → token, role, name
#            (Requirement 3.14)
# ---------------------------------------------------------------------------

class TestLogin(_BasePreservation):
    """
    Requirement 3.14 — POST /login with valid credentials returns a JWT token,
    the user's role, and the user's name.
    """

    def test_login_valid_credentials_returns_200(self):
        """POST /login with valid credentials returns HTTP 200."""
        self._require_client()
        resp = self.client.post(
            '/login',
            data=json.dumps({
                'email': _shared_email,
                'password': _shared_password
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 200,
            f"POST /login with valid credentials returned {resp.status_code}")

    def test_login_returns_token(self):
        """POST /login response contains a 'token' key."""
        self._require_client()
        resp = self.client.post(
            '/login',
            data=json.dumps({
                'email': _shared_email,
                'password': _shared_password
            }),
            content_type='application/json'
        )
        data = json.loads(resp.data)
        self.assertIn('token', data,
            f"POST /login response must contain 'token'. Got: {data}")
        self.assertIsInstance(data['token'], str)
        self.assertTrue(len(data['token']) > 0)

    def test_login_returns_role(self):
        """POST /login response contains a 'role' key."""
        self._require_client()
        resp = self.client.post(
            '/login',
            data=json.dumps({
                'email': _shared_email,
                'password': _shared_password
            }),
            content_type='application/json'
        )
        data = json.loads(resp.data)
        self.assertIn('role', data,
            f"POST /login response must contain 'role'. Got: {data}")

    def test_login_returns_name(self):
        """POST /login response contains a 'name' key."""
        self._require_client()
        resp = self.client.post(
            '/login',
            data=json.dumps({
                'email': _shared_email,
                'password': _shared_password
            }),
            content_type='application/json'
        )
        data = json.loads(resp.data)
        self.assertIn('name', data,
            f"POST /login response must contain 'name'. Got: {data}")
        self.assertEqual(data['name'], _shared_name,
            f"Expected name='{_shared_name}', got: {data['name']}")

    def test_login_invalid_credentials_returns_401(self):
        """POST /login with wrong password returns HTTP 401."""
        self._require_client()
        resp = self.client.post(
            '/login',
            data=json.dumps({
                'email': _shared_email,
                'password': 'WrongPassword!'
            }),
            content_type='application/json'
        )
        self.assertEqual(resp.status_code, 401,
            f"POST /login with wrong password returned {resp.status_code}, expected 401")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main(verbosity=2)
