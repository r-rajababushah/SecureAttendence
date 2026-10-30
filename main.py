"""Terminal application for the SecureAttendance hackathon prototype."""

import getpass
import json
from pathlib import Path

from attendance_store import AttendanceStore, sample_records
from auth import authenticate, password_is_valid, register_instructor
from crypto_utils import create_keys

BASE_DIR = Path(__file__).resolve().parent
AUTH_FILE = BASE_DIR / "secrets" / "instructor.json"
DATA_FILE = BASE_DIR / "data" / "attendance.enc"
SECRETS_DIR = BASE_DIR / "secrets"


def first_time_setup() -> None:
    print("\nWelcome to SecureAttendance — Team 3: Crusaders")
    print("First-time setup: create the first administrator account.")
    username = input("Create instructor username: ").strip()
    if not username:
        raise ValueError("Username cannot be empty.")
    while True:
        password = getpass.getpass("Create password (at least 10 characters): ")
        confirm = getpass.getpass("Re-enter password: ")
        if password != confirm:
            print("Passwords do not match. Try again.")
        elif not password_is_valid(password):
            print("Use at least 10 characters.")
        else:
            break
    create_keys(SECRETS_DIR)
    register_instructor(AUTH_FILE, username, password)
    AttendanceStore(DATA_FILE, SECRETS_DIR).save(sample_records())
    print("Setup complete. Your password was stored only as an Argon2id hash.")


def login() -> bool:
    for attempt in range(1, 4):
        username = input("Instructor username: ").strip()
        password = getpass.getpass("Password: ")
        if authenticate(AUTH_FILE, username, password):
            print("Login successful.")
            return True
        remaining = 3 - attempt
        print(f"Incorrect username or password. {remaining} attempt(s) remaining.")
    return False


def show_records(store: AttendanceStore) -> None:
    for student in store.load():
        print(f"\n{student['student_id']} — {student['name']}")
        for item in student["attendance"]:
            print(f"  {item['date']}: {item['status']} (updated {item['updated_at']})")


def edit_attendance(store: AttendanceStore) -> None:
    student_id = input("Student ID: ").strip().upper()
    status = input("Status (Present/Absent): ").strip().title()
    store.mark_attendance(student_id, status)
    print("Attendance saved in encrypted form.")


def tampering_demo(store: AttendanceStore) -> None:
    print("\n=== TAMPERING DETECTION DEMO ===\n")
    print("Original attendance file:", "Valid" if store.verify_file() else "Invalid")
    print("Creating temporary test copy...")
    print("Simulating unauthorized modification...")
    print("Checking HMAC...")
    try:
        passed = store.tampering_demo()
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Demo could not run: {error}")
        return
    if passed:
        print("RESULT: TAMPERING DETECTED!")
        print("Modified attendance data rejected.")
    else:
        print("RESULT: Demo failed to detect modification.")
    print("\nChecking original file...")
    print("Original file:", "VALID" if store.verify_file() else "INVALID")


def main() -> None:
    if not AUTH_FILE.exists():
        if DATA_FILE.exists() or (SECRETS_DIR / "encryption.key").exists() or (SECRETS_DIR / "hmac.key").exists():
            print("Setup files are incomplete. Restore the missing files from backup; refusing to generate replacement keys.")
            return
        try:
            first_time_setup()
        except (OSError, ValueError, FileExistsError) as error:
            print(f"Setup failed: {error}")
            return
    if not login():
        print("Login session ended after three failed attempts.")
        return

    store = AttendanceStore(DATA_FILE, SECRETS_DIR)
    while True:
        print("\n=== SecureAttendance ===")
        print("1. View all attendance records")
        print("2. Mark or update student attendance")
        print("3. Verify attendance file integrity")
        print("4. Run Tampering Detection Demo")
        print("5. Logout / Exit")
        choice = input("Choose an option: ").strip()
        try:
            if choice == "1":
                show_records(store)
            elif choice == "2":
                edit_attendance(store)
            elif choice == "3":
                print("Attendance file:", "VALID" if store.verify_file() else "INVALID — do not trust this data")
            elif choice == "4":
                tampering_demo(store)
            elif choice == "5":
                print("Logged out.")
                break
            else:
                print("Choose a number from 1 to 5.")
        except (OSError, ValueError, json.JSONDecodeError) as error:
            print(f"Operation failed: {error}")


if __name__ == "__main__":
    main()
