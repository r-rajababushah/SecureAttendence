"""Start SecureAttendance's local browser showcase with one command."""

import json
import secrets
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from pathlib import Path
from urllib.parse import urlparse

import unittest

from attendance_store import AttendanceStore, sample_records
from auth import (
    authenticate,
    create_instructor_account,
    get_account_role,
    has_permission,
    list_accounts,
    password_is_valid,
    register_admin,
)
from crypto_utils import create_keys

BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"
AUTH_FILE = BASE_DIR / "secrets" / "instructor.json"
DATA_FILE = BASE_DIR / "data" / "attendance.enc"
SECRETS_DIR = BASE_DIR / "secrets"
STORE = AttendanceStore(DATA_FILE, SECRETS_DIR)
SESSIONS: dict[str, dict[str, str]] = {}
LOGIN_FAILURES = 0
MAX_LOGIN_FAILURES = 3


class ShowcaseHandler(BaseHTTPRequestHandler):
    server_version = "SecureAttendanceShowcase/1.0"

    def log_message(self, _format, *_args):
        # Keep the terminal quiet while the presenter uses the browser UI.
        return

    def send_json(self, status: int, payload: dict, cookie: str | None = None) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.end_headers()
        self.wfile.write(body)

    def send_asset(self, path: Path, content_type: str) -> None:
        try:
            body = path.read_bytes()
        except OSError:
            self.send_error(404, "Showcase asset not found. Build the web app first.")
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def get_session(self) -> dict[str, str] | None:
        cookie = self.headers.get("Cookie", "")
        for item in cookie.split(";"):
            name, separator, value = item.strip().partition("=")
            if separator and name == "SecureAttendSession":
                return SESSIONS.get(value)
        return None

    def require_login(self) -> bool:
        if self.get_session():
            return True
        self.send_json(401, {"error": "Sign in to continue."})
        return False

    def require_permission(self, permission: str) -> bool:
        if not self.require_login():
            return False
        session = self.get_session()
        if session and has_permission(session.get("role", ""), permission):
            return True
        self.send_json(403, {"error": "Your account role is not allowed to perform this action."})
        return False

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length > 100_000:
            raise ValueError("Request is too large.")
        body = self.rfile.read(length)
        value = json.loads(body.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("Request must be a JSON object.")
        return value

    def do_GET(self) -> None:
        route = urlparse(self.path).path
        if route == "/":
            return self.send_asset(WEB_DIR / "index.html", "text/html; charset=utf-8")
        if route == "/assets/app.js":
            return self.send_asset(WEB_DIR / "assets" / "app.js", "text/javascript; charset=utf-8")
        if route == "/assets/styles.css":
            return self.send_asset(WEB_DIR / "src" / "styles.css", "text/css; charset=utf-8")
        if route == "/api/session":
            session = self.get_session()
            self.send_json(200, {
                "configured": AUTH_FILE.exists(),
                "authenticated": bool(session),
                "username": session.get("username") if session else None,
                "role": session.get("role") if session else None,
                "locked": LOGIN_FAILURES >= MAX_LOGIN_FAILURES,
            })
            return
        if route == "/api/records":
            if not self.require_permission("attendance:view"):
                return
            try:
                self.send_json(200, {"records": STORE.load()})
            except (OSError, ValueError, json.JSONDecodeError) as error:
                self.send_json(400, {"error": str(error)})
            return
        if route == "/api/accounts":
            if not self.require_permission("accounts:create"):
                return
            try:
                self.send_json(200, {"accounts": list_accounts(AUTH_FILE)})
            except (OSError, ValueError, json.JSONDecodeError) as error:
                self.send_json(400, {"error": str(error)})
            return
        self.send_json(404, {"error": "Page not found."})

    def do_POST(self) -> None:
        global LOGIN_FAILURES
        route = urlparse(self.path).path
        try:
            payload = self.read_json()
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError) as error:
            self.send_json(400, {"error": f"Invalid request: {error}"})
            return

        if route == "/api/register":
            if AUTH_FILE.exists():
                self.send_json(409, {"error": "An instructor account is already registered. Sign in instead."})
                return
            if DATA_FILE.exists() or (SECRETS_DIR / "encryption.key").exists() or (SECRETS_DIR / "hmac.key").exists():
                self.send_json(409, {"error": "Setup files are incomplete. Restore the original files from backup; replacement keys will not be generated."})
                return
            username = str(payload.get("username", "")).strip()
            password = str(payload.get("password", ""))
            if not username:
                self.send_json(400, {"error": "Enter an instructor username."})
                return
            if not password_is_valid(password):
                self.send_json(400, {"error": "Use a password with at least 10 characters."})
                return
            if password != payload.get("confirm_password"):
                self.send_json(400, {"error": "The passwords do not match."})
                return
            try:
                create_keys(SECRETS_DIR)
                register_admin(AUTH_FILE, username, password)
                STORE.save(sample_records())
                self.send_json(201, {"message": "Account created. Sign in to open the attendance dashboard."})
            except (OSError, ValueError, FileExistsError) as error:
                self.send_json(500, {"error": str(error)})
            return

        if route == "/api/login":
            if LOGIN_FAILURES >= MAX_LOGIN_FAILURES:
                self.send_json(429, {"error": "Three login attempts were used. Restart the showcase to begin a new login session."})
                return
            username = str(payload.get("username", "")).strip()
            password = str(payload.get("password", ""))
            if authenticate(AUTH_FILE, username, password):
                LOGIN_FAILURES = 0
                token = secrets.token_urlsafe(32)
                role = get_account_role(AUTH_FILE, username) or "instructor"
                SESSIONS[token] = {"username": username, "role": role}
                self.send_json(200, {"username": username, "role": role}, f"SecureAttendSession={token}; HttpOnly; SameSite=Strict; Path=/; Max-Age=28800")
            else:
                LOGIN_FAILURES += 1
                remaining = MAX_LOGIN_FAILURES - LOGIN_FAILURES
                self.send_json(401, {"error": "Username or password is incorrect.", "attempts_remaining": remaining, "locked": remaining == 0})
            return

        if route == "/api/logout":
            cookie = self.headers.get("Cookie", "")
            for item in cookie.split(";"):
                name, separator, value = item.strip().partition("=")
                if separator and name == "SecureAttendSession":
                    SESSIONS.pop(value, None)
            self.send_json(200, {"message": "Signed out."}, "SecureAttendSession=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0")
            return

        if route == "/api/attendance":
            if not self.require_permission("attendance:mark"):
                return
            student_id = str(payload.get("student_id", "")).strip().upper()
            status = str(payload.get("status", ""))
            try:
                STORE.mark_attendance(student_id, status)
                self.send_json(200, {"message": f"{student_id} marked {status}. Attendance was saved encrypted."})
            except (OSError, ValueError, json.JSONDecodeError) as error:
                self.send_json(400, {"error": str(error)})
            return

        if route == "/api/verify":
            if not self.require_permission("integrity:verify"):
                return
            valid = STORE.verify_file()
            self.send_json(200, {"valid": valid, "message": "Attendance file integrity is valid." if valid else "Integrity check failed. Do not trust this attendance file."})
            return

        if route == "/api/tampering-demo":
            if not self.require_permission("demo:tamper"):
                return
            try:
                detected = STORE.tampering_demo()
                original_valid = STORE.verify_file()
                self.send_json(200, {"detected": detected, "original_valid": original_valid})
            except (OSError, ValueError, json.JSONDecodeError) as error:
                self.send_json(400, {"error": str(error)})
            return

        if route == "/api/tests":
            if not self.require_permission("tests:run"):
                return
            output = StringIO()
            suite = unittest.defaultTestLoader.discover(str(BASE_DIR / "tests"), pattern="test*.py")
            result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
            self.send_json(200, {"passed": result.wasSuccessful(), "output": output.getvalue(), "tests_run": result.testsRun, "failures": len(result.failures) + len(result.errors)})
            return

        if route == "/api/accounts/create":
            if not self.require_permission("accounts:create"):
                return
            session = self.get_session() or {}
            username = str(payload.get("username", "")).strip()
            password = str(payload.get("password", ""))
            if password != payload.get("confirm_password"):
                self.send_json(400, {"error": "The passwords do not match."})
                return
            try:
                create_instructor_account(AUTH_FILE, session.get("username", ""), username, password)
                self.send_json(201, {"message": f"Instructor account {username} created.", "accounts": list_accounts(AUTH_FILE)})
            except PermissionError as error:
                self.send_json(403, {"error": str(error)})
            except (OSError, ValueError, json.JSONDecodeError) as error:
                self.send_json(400, {"error": str(error)})
            return

        self.send_json(404, {"error": "Action not found."})


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), ShowcaseHandler)
    server.daemon_threads = True
    address, port = server.server_address
    url = f"http://{address}:{port}/"
    print("SecureAttendance showcase is running in your browser. Press Ctrl+C to stop it.")
    print(url)
    threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nSecureAttendance showcase stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
