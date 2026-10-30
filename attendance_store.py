"""Encrypted attendance storage and simple record operations."""

import json
import os
import tempfile
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from crypto_utils import decrypt_bytes, encrypt_bytes, load_key


def sample_records() -> list[dict]:
    today = date.today().isoformat()
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    return [
        {"student_id": "S101", "name": "Aditi Sharma", "attendance": [{"date": today, "status": "Absent", "updated_at": now}]},
        {"student_id": "S102", "name": "Rahul Verma", "attendance": [{"date": today, "status": "Absent", "updated_at": now}]},
        {"student_id": "S103", "name": "Neha Singh", "attendance": [{"date": today, "status": "Absent", "updated_at": now}]},
    ]


def validate_status(status: str) -> str:
    if status not in ("Present", "Absent"):
        raise ValueError("Status must be exactly Present or Absent.")
    return status


class AttendanceStore:
    def __init__(self, data_file: Path, secrets_dir: Path):
        self.data_file = Path(data_file)
        self.secrets_dir = Path(secrets_dir)

    def _keys(self) -> tuple[bytes, bytes]:
        return load_key(self.secrets_dir / "encryption.key"), load_key(self.secrets_dir / "hmac.key")

    def save(self, records: list[dict]) -> None:
        enc_key, mac_key = self._keys()
        envelope = encrypt_bytes(json.dumps(records, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), enc_key, mac_key)
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        # Atomic replacement prevents a partial write if the program is interrupted.
        fd, temporary_name = tempfile.mkstemp(dir=self.data_file.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(envelope, file, indent=2)
                file.flush()
                os.fsync(file.fileno())
            Path(temporary_name).replace(self.data_file)
            try:
                self.data_file.chmod(0o600)
            except OSError:
                pass
        finally:
            Path(temporary_name).unlink(missing_ok=True)

    def load(self) -> list[dict]:
        if not self.data_file.exists():
            raise FileNotFoundError(f"Attendance file is missing: {self.data_file}")
        enc_key, mac_key = self._keys()
        envelope = json.loads(self.data_file.read_text(encoding="utf-8"))
        plaintext = decrypt_bytes(envelope, enc_key, mac_key)
        records = json.loads(plaintext.decode("utf-8"))
        if not isinstance(records, list):
            raise ValueError("Attendance data has an invalid structure.")
        return records

    def mark_attendance(self, student_id: str, status: str, on_date: Optional[date] = None) -> None:
        validate_status(status)
        records = self.load()
        student = next((row for row in records if row.get("student_id") == student_id), None)
        if student is None:
            raise ValueError("Unknown student ID.")
        day = (on_date or date.today()).isoformat()
        stamp = datetime.now().astimezone().isoformat(timespec="seconds")
        entry = next((item for item in student["attendance"] if item["date"] == day), None)
        if entry:
            entry.update(status=status, updated_at=stamp)
        else:
            student["attendance"].append({"date": day, "status": status, "updated_at": stamp})
        self.save(records)

    def verify_file(self, path: Optional[Path] = None) -> bool:
        """Verify the stored envelope HMAC without decrypting attendance."""
        from crypto_utils import verify_envelope

        target = Path(path) if path else self.data_file
        try:
            envelope = json.loads(target.read_text(encoding="utf-8"))
            _, mac_key = self._keys()
            return verify_envelope(envelope, mac_key)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return False

    def tampering_demo(self) -> bool:
        """Return True when a changed temporary ciphertext is rejected and original remains valid."""
        if not self.verify_file():
            raise ValueError("Original attendance file is not valid; demo stopped.")
        original = json.loads(self.data_file.read_text(encoding="utf-8"))
        modified = dict(original)
        cipher = modified["ciphertext"]
        if not cipher:
            raise ValueError("Ciphertext is empty; cannot demonstrate modification.")
        modified["ciphertext"] = ("0" if cipher[0] != "0" else "1") + cipher[1:]
        fd, temp_name = tempfile.mkstemp(dir=self.data_file.parent, prefix="tamper-demo-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(modified, file)
            detected = not self.verify_file(Path(temp_name))
        finally:
            Path(temp_name).unlink(missing_ok=True)
        return detected and self.verify_file()
