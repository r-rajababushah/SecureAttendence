"""Password authentication, account storage, and role permissions."""

import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

PASSWORD_HASHER = PasswordHasher()

ROLE_PERMISSIONS = {
    "admin": frozenset({"attendance:view", "attendance:mark", "integrity:verify", "demo:tamper", "tests:run", "accounts:create"}),
    "instructor": frozenset({"attendance:view", "attendance:mark", "integrity:verify", "demo:tamper", "tests:run"}),
}


def _load_auth_data(auth_file: Path) -> dict:
    """Read the current account format or adapt the original single-account format."""
    saved = json.loads(auth_file.read_text(encoding="utf-8"))
    if isinstance(saved.get("users"), list):
        return saved
    # Older project versions had one username and password hash. Treat that
    # original account as the local administrator so existing demos still work.
    if saved.get("username") and saved.get("password_hash"):
        return {
            "version": 2,
            "users": [{
                "username": saved["username"],
                "password_hash": saved["password_hash"],
                "role": "admin",
                "created_at": "Legacy account",
            }],
        }
    raise ValueError("Instructor account file has an invalid format.")


def _save_auth_data(auth_file: Path, data: dict) -> None:
    auth_file.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(dir=auth_file.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, ensure_ascii=False)
            file.flush()
            os.fsync(file.fileno())
        Path(temporary_name).replace(auth_file)
        try:
            auth_file.chmod(0o600)
        except OSError:
            pass
    finally:
        Path(temporary_name).unlink(missing_ok=True)


def _validate_new_account(auth_file: Path, username: str, password: str) -> dict:
    if not username or username.strip() != username:
        raise ValueError("Username cannot be empty or have surrounding spaces.")
    if not password_is_valid(password):
        raise ValueError("Password must contain at least 10 characters.")
    if auth_file.exists():
        return _load_auth_data(auth_file)
    return {"version": 2, "users": []}


def register_admin(auth_file: Path, username: str, password: str) -> None:
    """Create the first account; it receives administrator privileges."""
    data = _validate_new_account(auth_file, username, password)
    if data["users"]:
        raise FileExistsError("An account is already registered. Sign in as an administrator to add instructors.")
    data["users"].append({
        "username": username,
        "password_hash": PASSWORD_HASHER.hash(password),
        "role": "admin",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    })
    _save_auth_data(auth_file, data)


def register_instructor(auth_file: Path, username: str, password: str) -> None:
    """Backward-compatible alias for creating the initial administrator."""
    register_admin(auth_file, username, password)


def create_instructor_account(auth_file: Path, created_by: str, username: str, password: str) -> None:
    """Allow only an administrator to create another instructor account."""
    data = _validate_new_account(auth_file, username, password)
    creator = next((user for user in data["users"] if user.get("username", "").casefold() == created_by.casefold()), None)
    if not creator or creator.get("role") != "admin":
        raise PermissionError("Only an administrator can create instructor accounts.")
    if any(user.get("username", "").casefold() == username.casefold() for user in data["users"]):
        raise ValueError("That username is already in use.")
    data["users"].append({
        "username": username,
        "password_hash": PASSWORD_HASHER.hash(password),
        "role": "instructor",
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    })
    _save_auth_data(auth_file, data)


def authenticate(auth_file: Path, username: str, password: str) -> bool:
    """Return True only when a saved account's password matches its hash."""
    try:
        data = _load_auth_data(auth_file)
        user = next((item for item in data["users"] if item.get("username", "").casefold() == username.casefold()), None)
        if user is None:
            return False
        PASSWORD_HASHER.verify(user["password_hash"], password)
        return True
    except (OSError, ValueError, KeyError, TypeError, VerificationError, VerifyMismatchError):
        return False


def get_account_role(auth_file: Path, username: str) -> str | None:
    """Return a saved user's role, including the compatible legacy admin role."""
    try:
        data = _load_auth_data(auth_file)
        user = next((item for item in data["users"] if item.get("username", "").casefold() == username.casefold()), None)
        return user.get("role", "instructor") if user else None
    except (OSError, ValueError, KeyError, TypeError):
        return None


def list_accounts(auth_file: Path) -> list[dict]:
    """Return account labels safe for display; never include password hashes."""
    data = _load_auth_data(auth_file)
    return [{"username": user["username"], "role": user.get("role", "instructor"), "created_at": user.get("created_at", "—")} for user in data["users"]]


def has_permission(role: str, permission: str) -> bool:
    """Check whether the role is allowed to perform a named action."""
    return permission in ROLE_PERMISSIONS.get(role, frozenset())


def password_is_valid(password: str) -> bool:
    """Require a useful minimum length without imposing confusing rules."""
    return len(password) >= 10
