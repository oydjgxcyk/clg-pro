"""
Bug Condition Exploration Tests — Task 1
========================================
**Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5, 1.9, 1.12, 1.15, 1.17,
             1.20, 1.22, 1.25, 1.27, 1.29, 1.30, 1.31, 1.32, 1.33**

CRITICAL: These tests are EXPECTED TO FAIL on unfixed code.
Failure confirms the bugs exist. DO NOT fix the code to make these pass.
They will pass only after the full bugfix implementation (Task 10).

Property 1: Bug Condition — Hardcoded Identity, Undefined JS Functions,
            Missing Routes
"""

import os
import re
import sys
import unittest
import threading
import time

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


def _read_html(filename: str) -> str:
    """Read an HTML file from the project root."""
    path = os.path.join(PROJECT_ROOT, filename)
    with open(path, 'r', encoding='utf-8') as fh:
        return fh.read()


# ---------------------------------------------------------------------------
# Test A — Backend routes: missing routes return 404 on unfixed code
# ---------------------------------------------------------------------------

class TestA_BackendRoutes(unittest.TestCase):
    """
    Test A — Backend routes
    Calls GET /student/profile, PUT /dean/reject/1, GET /security/stats.
    On UNFIXED code these routes do not exist → Flask returns 404.
    EXPECTED FAILURE: AssertionError because status code is 404, not 200.
    """

    @classmethod
    def setUpClass(cls):
        """Import the Flask app and create a test client."""
        # We need to import app without actually running it.
        # Temporarily add project root to sys.path.
        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)

        # Import inside a try/except so that an ImportError (e.g. missing
        # qrcode) is surfaced as a test error rather than a collection error.
        try:
            import app as flask_app
            with flask_app.app.app_context():
                flask_app.db.create_all()
            cls.client = flask_app.app.test_client()
            cls.import_error = None
        except Exception as exc:
            cls.client = None
            cls.import_error = exc

    def _require_client(self):
        if self.client is None:
            self.fail(
                f"Could not import app.py — import raised: {self.import_error}"
            )

    def test_A1_student_profile_returns_200(self):
        """GET /student/profile should return HTTP 200 (not 404)."""
        self._require_client()
        response = self.client.get('/student/profile')
        self.assertEqual(
            response.status_code, 200,
            f"GET /student/profile returned {response.status_code} — "
            "route is missing (Bug 1.31)"
        )

    def test_A2_dean_reject_returns_200(self):
        """PUT /dean/reject/1 should return HTTP 200 (not 404)."""
        self._require_client()
        response = self.client.put('/dean/reject/1')
        self.assertEqual(
            response.status_code, 200,
            f"PUT /dean/reject/1 returned {response.status_code} — "
            "route is missing (Bug 1.29)"
        )

    def test_A3_security_stats_returns_200(self):
        """GET /security/stats should return HTTP 200 (not 404)."""
        self._require_client()
        response = self.client.get('/security/stats')
        self.assertEqual(
            response.status_code, 200,
            f"GET /security/stats returned {response.status_code} — "
            "route is missing (Bug 1.33)"
        )


# ---------------------------------------------------------------------------
# Test B — Model field: created_at column missing on unfixed code
# ---------------------------------------------------------------------------

class TestB_ModelField(unittest.TestCase):
    """
    Test B — Model field
    Inspects OutpassRequest.__table__.columns for 'created_at'.
    On UNFIXED code the column does not exist.
    EXPECTED FAILURE: AssertionError because 'created_at' is absent.
    """

    @classmethod
    def setUpClass(cls):
        if PROJECT_ROOT not in sys.path:
            sys.path.insert(0, PROJECT_ROOT)
        try:
            import app as flask_app
            cls.OutpassRequest = flask_app.OutpassRequest
            cls.import_error = None
        except Exception as exc:
            cls.OutpassRequest = None
            cls.import_error = exc

    def test_B_created_at_column_exists(self):
        """OutpassRequest model must have a 'created_at' column (Bug 1.32)."""
        if self.OutpassRequest is None:
            self.fail(
                f"Could not import app.py — import raised: {self.import_error}"
            )
        column_names = [
            col.name for col in self.OutpassRequest.__table__.columns
        ]
        self.assertIn(
            'created_at', column_names,
            f"'created_at' not found in OutpassRequest columns: "
            f"{column_names} — Bug 1.32"
        )


# ---------------------------------------------------------------------------
# Test C — App startup: ImportError when qrcode is absent
# ---------------------------------------------------------------------------

class TestC_AppStartup(unittest.TestCase):
    """
    Test C — App startup
    Simulates qrcode being absent by patching sys.modules, then re-imports
    app.py. On UNFIXED code the top-level 'import qrcode' raises ImportError.
    EXPECTED FAILURE: ImportError is raised instead of being handled.
    """

    def test_C_app_imports_without_qrcode(self):
        """
        app.py must import cleanly even when qrcode is not installed.
        (Bug 1.30)
        """
        import importlib
        import types

        # Remove any cached import of 'app' so we get a fresh import.
        for mod_name in list(sys.modules.keys()):
            if mod_name == 'app' or mod_name.startswith('app.'):
                del sys.modules[mod_name]

        # Inject a fake 'qrcode' that raises ImportError on import.
        # We do this by temporarily replacing it with a module that raises
        # when accessed, simulating the package being absent.
        original_qrcode = sys.modules.pop('qrcode', None)

        # Create a broken finder that raises ImportError for 'qrcode'.
        class _BlockQRCode:
            def find_module(self, name, path=None):
                if name == 'qrcode' or name.startswith('qrcode.'):
                    return self
                return None

            def load_module(self, name):
                raise ImportError(
                    f"Simulated missing package: {name}"
                )

        blocker = _BlockQRCode()
        sys.meta_path.insert(0, blocker)

        try:
            # This should NOT raise ImportError if the app handles it.
            importlib.import_module('app')
        except ImportError as exc:
            self.fail(
                f"app.py raised ImportError when qrcode is absent: {exc} — "
                "Bug 1.30: top-level 'import qrcode' must be guarded"
            )
        finally:
            # Restore original state.
            sys.meta_path.remove(blocker)
            if original_qrcode is not None:
                sys.modules['qrcode'] = original_qrcode
            # Clean up the freshly imported app module.
            for mod_name in list(sys.modules.keys()):
                if mod_name == 'app' or mod_name.startswith('app.'):
                    del sys.modules[mod_name]


# ---------------------------------------------------------------------------
# Test D — Static folder: static/qr/ directory must exist
# ---------------------------------------------------------------------------

class TestD_StaticFolder(unittest.TestCase):
    """
    Test D — Static folder
    Asserts that static/qr/ exists at the project root.
    On UNFIXED code neither static/ nor static/qr/ exists.
    EXPECTED FAILURE: AssertionError because the directory is absent.
    """

    def test_D_static_qr_directory_exists(self):
        """static/qr/ directory must exist so Flask can serve QR images (Bug 1.27/1.28)."""
        qr_dir = os.path.join(PROJECT_ROOT, 'static', 'qr')
        self.assertTrue(
            os.path.isdir(qr_dir),
            f"Directory '{qr_dir}' does not exist — "
            "Bug 1.27/1.28: static/qr/ must be created"
        )


# ---------------------------------------------------------------------------
# Test E — JS functions: submitReq, resetForm, loadHistory, loadQR undefined
# ---------------------------------------------------------------------------

class TestE_JSFunctions(unittest.TestCase):
    """
    Test E — JS functions
    Reads student_dashboard.html and checks that the four functions are
    *defined* (i.e., appear as 'function submitReq', 'function resetForm',
    etc.) inside a <script> block — not merely referenced in onclick attrs.
    On UNFIXED code these functions are absent from the script block.
    EXPECTED FAILURE: AssertionError for each missing function.
    """

    REQUIRED_FUNCTIONS = ['submitReq', 'resetForm', 'loadHistory', 'loadQR']

    @classmethod
    def setUpClass(cls):
        cls.html = _read_html('student_dashboard.html')

    def _extract_script_content(self) -> str:
        """Return the concatenated text of all <script> blocks."""
        scripts = re.findall(
            r'<script[^>]*>(.*?)</script>',
            self.html,
            re.DOTALL | re.IGNORECASE
        )
        return '\n'.join(scripts)

    def _is_function_defined(self, name: str, script: str) -> bool:
        """
        Return True if the function is defined (not just referenced).
        Matches patterns like:
          function submitReq(
          async function submitReq(
          const submitReq = function(
          const submitReq = async function(
          const submitReq = (
          const submitReq = async (
        """
        patterns = [
            rf'\bfunction\s+{re.escape(name)}\s*\(',
            rf'\basync\s+function\s+{re.escape(name)}\s*\(',
            rf'\bconst\s+{re.escape(name)}\s*=\s*(async\s+)?function\s*\(',
            rf'\bconst\s+{re.escape(name)}\s*=\s*(async\s+)?\(',
        ]
        return any(re.search(p, script) for p in patterns)

    def test_E1_submitReq_defined(self):
        """submitReq must be defined as a function in student_dashboard.html (Bug 1.2)."""
        script = self._extract_script_content()
        self.assertTrue(
            self._is_function_defined('submitReq', script),
            "submitReq is not defined as a function in student_dashboard.html — Bug 1.2"
        )

    def test_E2_resetForm_defined(self):
        """resetForm must be defined as a function in student_dashboard.html (Bug 1.3)."""
        script = self._extract_script_content()
        self.assertTrue(
            self._is_function_defined('resetForm', script),
            "resetForm is not defined as a function in student_dashboard.html — Bug 1.3"
        )

    def test_E3_loadHistory_defined(self):
        """loadHistory must be defined as a function in student_dashboard.html (Bug 1.4)."""
        script = self._extract_script_content()
        self.assertTrue(
            self._is_function_defined('loadHistory', script),
            "loadHistory is not defined as a function in student_dashboard.html — Bug 1.4"
        )

    def test_E4_loadQR_defined(self):
        """loadQR must be defined as a function in student_dashboard.html (Bug 1.5)."""
        script = self._extract_script_content()
        self.assertTrue(
            self._is_function_defined('loadQR', script),
            "loadQR is not defined as a function in student_dashboard.html — Bug 1.5"
        )


# ---------------------------------------------------------------------------
# Test F — Hardcoded strings: dashboards must not contain literal names
# ---------------------------------------------------------------------------

class TestF_HardcodedStrings(unittest.TestCase):
    """
    Test F — Hardcoded strings
    Reads each dashboard HTML file and asserts that none of the known
    hardcoded identity strings appear in the source.
    On UNFIXED code every dashboard contains at least one of these strings.
    EXPECTED FAILURE: AssertionError for each file that still has them.
    """

    HARDCODED_STRINGS = [
        "Elakkiya S.",
        "Prof. Jane Doe",
        "Dr. Robert Smith",
        "Dr. Head of Dept",
        "Officer Davis",
        "John Doe",
    ]

    DASHBOARD_FILES = [
        'student_dashboard.html',
        'mentor_dashboard.html',
        'parent_dashboard.html',
        'hod_dashboard.html',
        'dean_dashboard.html',
        'security_dashboard.html',
    ]

    def _check_file(self, filename: str):
        html = _read_html(filename)
        found = [s for s in self.HARDCODED_STRINGS if s in html]
        self.assertEqual(
            found, [],
            f"{filename} contains hardcoded identity strings: {found} — "
            "Bugs 1.1, 1.9, 1.12, 1.15, 1.17, 1.22"
        )

    def test_F1_student_dashboard_no_hardcoded_strings(self):
        """student_dashboard.html must not contain hardcoded identity strings (Bug 1.1)."""
        self._check_file('student_dashboard.html')

    def test_F2_mentor_dashboard_no_hardcoded_strings(self):
        """mentor_dashboard.html must not contain hardcoded identity strings (Bug 1.9)."""
        self._check_file('mentor_dashboard.html')

    def test_F3_parent_dashboard_no_hardcoded_strings(self):
        """parent_dashboard.html must not contain hardcoded identity strings (Bug 1.12)."""
        self._check_file('parent_dashboard.html')

    def test_F4_hod_dashboard_no_hardcoded_strings(self):
        """hod_dashboard.html must not contain hardcoded identity strings (Bug 1.15)."""
        self._check_file('hod_dashboard.html')

    def test_F5_dean_dashboard_no_hardcoded_strings(self):
        """dean_dashboard.html must not contain hardcoded identity strings (Bug 1.17)."""
        self._check_file('dean_dashboard.html')

    def test_F6_security_dashboard_no_hardcoded_strings(self):
        """security_dashboard.html must not contain hardcoded identity strings (Bug 1.22)."""
        self._check_file('security_dashboard.html')


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    unittest.main(verbosity=2)
