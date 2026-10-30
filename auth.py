"""Instructor registration and password verification."""

import json
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

PASSWORD_HASHER = PasswordHasher()


def register_instructor(auth_file: Path, username: str, password: str) -> None:
    """Save an instructor username and Argon2id hash, never the password."""
    if not username or username.strip() != username:
        raise ValueError("Username cannot be empty or have surrounding spaces.")
    if not password_is_valid(password):
        raise ValueError("Password must contain at least 10 characters.")
    auth_file.parent.mkdir(parents=True, exist_ok=True)
    auth_file.write_text(
        json.dumps({"username": username, "password_hash": PASSWORD_HASHER.hash(password)}, indent=2),
        encoding="utf-8",
    )
    try:
        auth_file.chmod(0o600)
    except OSError:
        pass


def authenticate(auth_file: Path, username: str, password: str) -> bool:
    """Return True only when both username and password match."""
    try:
        saved = json.loads(auth_file.read_text(encoding="utf-8"))
        if username != saved["username"]:
            return False
        PASSWORD_HASHER.verify(saved["password_hash"], password)
        return True
    except (OSError, ValueError, KeyError, TypeError, VerificationError, VerifyMismatchError):
        return False


def password_is_valid(password: str) -> bool:
    """Require a useful minimum length without imposing confusing rules."""
    return len(password) >= 10
