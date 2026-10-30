"""Optional Tkinter desktop interface for the SecureAttendance prototype."""

import json
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Optional

from attendance_store import AttendanceStore, sample_records
from auth import authenticate, password_is_valid, register_instructor
from crypto_utils import create_keys

BASE_DIR = Path(__file__).resolve().parent
AUTH_FILE = BASE_DIR / "secrets" / "instructor.json"
DATA_FILE = BASE_DIR / "data" / "attendance.enc"
SECRETS_DIR = BASE_DIR / "secrets"

NAVY = "#172B4D"
TEAL = "#087E8B"
PAGE = "#F3F6FA"
INK = "#23334D"
MUTED = "#64748B"
GREEN = "#16805D"
RED = "#B54747"


class SecureAttendanceApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("SecureAttendance | Team 3 – Crusaders")
        self.root.geometry("1060x720")
        self.root.minsize(860, 620)
        self.root.configure(bg=PAGE)
        self.store = AttendanceStore(DATA_FILE, SECRETS_DIR)
        self.failed_attempts = 0
        self.current_username = ""
        self.student_choices: dict[str, str] = {}
        self.style = ttk.Style()
        self.style.configure("Treeview", rowheight=34, font=("Helvetica", 11), background="white", fieldbackground="white", foreground=INK)
        self.style.configure("Treeview.Heading", font=("Helvetica", 10, "bold"), foreground=NAVY)
        self.style.map("Treeview", background=[("selected", "#DCEFF1")], foreground=[("selected", INK)])
        self.show_entry_screen()

    def clear(self) -> None:
        for child in self.root.winfo_children():
            child.destroy()

    def make_header(self, title: str, subtitle: str) -> None:
        header = tk.Frame(self.root, bg=NAVY, padx=30, pady=22)
        header.pack(fill="x")
        tk.Label(header, text="SECUREATTENDANCE", bg=NAVY, fg="#8DE0D1", font=("Helvetica", 10, "bold")).pack(anchor="w")
        tk.Label(header, text=title, bg=NAVY, fg="white", font=("Helvetica", 23, "bold")).pack(anchor="w", pady=(5, 2))
        tk.Label(header, text=subtitle, bg=NAVY, fg="#D1DAE8", font=("Helvetica", 11)).pack(anchor="w")

    def show_entry_screen(self) -> None:
        self.clear()
        if AUTH_FILE.exists():
            self.show_login()
        elif DATA_FILE.exists() or (SECRETS_DIR / "encryption.key").exists() or (SECRETS_DIR / "hmac.key").exists():
            self.make_header("Setup needs attention", "SecureAttendance · Team 3 – Crusaders")
            tk.Label(
                self.root,
                text="Some setup files exist, but the instructor account is missing.\nRestore the original files from backup; replacement keys are never generated automatically.",
                bg=PAGE,
                fg=INK,
                font=("Helvetica", 13),
                justify="left",
                padx=40,
                pady=35,
            ).pack(anchor="w")
        else:
            self.show_registration()

    def card(self, parent: tk.Widget, padding: int = 28) -> tk.Frame:
        return tk.Frame(parent, bg="white", padx=padding, pady=padding, highlightthickness=1, highlightbackground="#E2E8F0")

    def make_field(self, parent: tk.Widget, label: str, show: Optional[str] = None) -> tk.Entry:
        tk.Label(parent, text=label, bg="white", fg=INK, font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(12, 5))
        field = tk.Entry(parent, show=show or "", relief="solid", bd=1, highlightthickness=0, font=("Helvetica", 12), width=34)
        field.pack(fill="x", ipady=8)
        return field

    def primary_button(self, parent: tk.Widget, text: str, command) -> tk.Button:
        return tk.Button(parent, text=text, command=command, bg=TEAL, fg="white", activebackground="#066B76", activeforeground="white", relief="flat", bd=0, padx=18, pady=11, font=("Helvetica", 11, "bold"), cursor="hand2")

    def show_registration(self) -> None:
        self.clear()
        self.make_header("Welcome, instructor", "Create your protected account to set up the attendance demo.")
        area = tk.Frame(self.root, bg=PAGE, padx=30, pady=24)
        area.pack(fill="both", expand=True)
        card = self.card(area, 30)
        card.pack(anchor="n", pady=8)
        tk.Label(card, text="First-time setup", bg="white", fg=NAVY, font=("Helvetica", 18, "bold")).pack(anchor="w")
        tk.Label(card, text="Your password is hashed. It is never saved as plain text.", bg="white", fg=MUTED, font=("Helvetica", 10)).pack(anchor="w", pady=(5, 4))
        self.username_entry = self.make_field(card, "Instructor username")
        self.password_entry = self.make_field(card, "Create password · at least 10 characters", "*")
        self.confirm_entry = self.make_field(card, "Confirm password", "*")
        self.primary_button(card, "Create account and secure demo", self.register).pack(fill="x", pady=(22, 0))

    def register(self) -> None:
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()
        if not username:
            messagebox.showerror("Username required", "Enter an instructor username.", parent=self.root)
            return
        if password != confirm:
            messagebox.showerror("Passwords do not match", "Enter the same password in both fields.", parent=self.root)
            return
        if not password_is_valid(password):
            messagebox.showerror("Password too short", "Use at least 10 characters.", parent=self.root)
            return
        try:
            create_keys(SECRETS_DIR)
            register_instructor(AUTH_FILE, username, password)
            self.store.save(sample_records())
        except (OSError, ValueError, FileExistsError) as error:
            messagebox.showerror("Setup failed", str(error), parent=self.root)
            return
        messagebox.showinfo("Setup complete", "Your instructor account and encrypted sample attendance are ready. Please log in.", parent=self.root)
        self.show_login()

    def show_login(self) -> None:
        self.clear()
        self.make_header("Instructor sign in", "Attendance is shown only after your identity is verified.")
        area = tk.Frame(self.root, bg=PAGE, padx=30, pady=30)
        area.pack(fill="both", expand=True)
        card = self.card(area, 34)
        card.pack(anchor="n", pady=14)
        tk.Label(card, text="Sign in to continue", bg="white", fg=NAVY, font=("Helvetica", 18, "bold")).pack(anchor="w")
        self.username_entry = self.make_field(card, "Username")
        self.password_entry = self.make_field(card, "Password", "*")
        self.primary_button(card, "Sign in", self.login).pack(fill="x", pady=(24, 0))
        self.password_entry.bind("<Return>", lambda _event: self.login())
        self.username_entry.focus_set()

    def login(self) -> None:
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        if authenticate(AUTH_FILE, username, password):
            self.failed_attempts = 0
            self.current_username = username
            self.show_dashboard()
            return
        self.failed_attempts += 1
        remaining = 3 - self.failed_attempts
        if remaining == 0:
            messagebox.showerror("Login locked", "Three attempts used. Close and reopen the app to start a new login session.", parent=self.root)
            self.root.destroy()
        else:
            messagebox.showerror("Sign in failed", f"Username or password is incorrect. {remaining} attempt(s) remain.", parent=self.root)
            self.password_entry.delete(0, tk.END)
            self.password_entry.focus_set()

    def show_dashboard(self) -> None:
        self.clear()
        header = tk.Frame(self.root, bg=NAVY, padx=26, pady=18)
        header.pack(fill="x")
        top = tk.Frame(header, bg=NAVY)
        top.pack(fill="x")
        title_area = tk.Frame(top, bg=NAVY)
        title_area.pack(side="left", fill="x", expand=True)
        tk.Label(title_area, text="SECUREATTENDANCE  /  TEAM 3 · CRUSADERS", bg=NAVY, fg="#8DE0D1", font=("Helvetica", 9, "bold")).pack(anchor="w")
        tk.Label(title_area, text="Attendance dashboard", bg=NAVY, fg="white", font=("Helvetica", 22, "bold")).pack(anchor="w", pady=(4, 0))
        tk.Label(title_area, text=f"Signed in as {self.current_username}", bg=NAVY, fg="#D1DAE8", font=("Helvetica", 10)).pack(anchor="w", pady=(3, 0))
        tk.Button(top, text="Log out", command=self.show_login, bg="#2D4262", fg="white", activebackground="#405777", activeforeground="white", relief="flat", padx=15, pady=9, font=("Helvetica", 10, "bold")).pack(side="right", anchor="n")

        body = tk.Frame(self.root, bg=PAGE, padx=24, pady=18)
        body.pack(fill="both", expand=True)
        self.stats_frame = tk.Frame(body, bg=PAGE)
        self.stats_frame.pack(fill="x", pady=(0, 15))

        table_card = tk.Frame(body, bg="white", padx=16, pady=15, highlightthickness=1, highlightbackground="#E2E8F0")
        table_card.pack(fill="both", expand=True)
        table_title = tk.Frame(table_card, bg="white")
        table_title.pack(fill="x", pady=(0, 12))
        tk.Label(table_title, text="Attendance records", bg="white", fg=NAVY, font=("Helvetica", 15, "bold")).pack(side="left")
        tk.Label(table_title, text="Encrypted at rest · HMAC protected", bg="white", fg=MUTED, font=("Helvetica", 9)).pack(side="right", anchor="s")

        table_wrap = tk.Frame(table_card, bg="white")
        table_wrap.pack(fill="both", expand=True)
        columns = ("student_id", "name", "date", "status", "updated")
        self.table = ttk.Treeview(table_wrap, columns=columns, show="headings", selectmode="browse")
        headings = {"student_id": "STUDENT ID", "name": "STUDENT", "date": "DATE", "status": "STATUS", "updated": "LAST UPDATED"}
        widths = {"student_id": 110, "name": 190, "date": 120, "status": 110, "updated": 230}
        for column in columns:
            self.table.heading(column, text=headings[column])
            self.table.column(column, width=widths[column], minwidth=80, anchor="w")
        scrollbar = ttk.Scrollbar(table_wrap, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.table.tag_configure("Present", foreground=GREEN)
        self.table.tag_configure("Absent", foreground=RED)

        actions = tk.Frame(body, bg=PAGE, pady=13)
        actions.pack(fill="x")
        self.make_edit_panel(actions).pack(side="left", fill="x", expand=True)
        button_column = tk.Frame(actions, bg=PAGE, padx=14)
        button_column.pack(side="right", fill="y")
        self.action_button(button_column, "Verify integrity", self.verify_integrity).pack(fill="x", pady=(0, 8))
        self.action_button(button_column, "Run tampering demo", self.run_tampering_demo, highlighted=True).pack(fill="x", pady=(0, 8))
        self.action_button(button_column, "Run all security tests", self.show_test_runner).pack(fill="x")
        self.refresh_records()

    def action_button(self, parent: tk.Widget, text: str, command, highlighted: bool = False) -> tk.Button:
        background = TEAL if highlighted else "white"
        foreground = "white" if highlighted else NAVY
        return tk.Button(parent, text=text, command=command, bg=background, fg=foreground, activebackground=TEAL, activeforeground="white", relief="solid" if not highlighted else "flat", bd=1 if not highlighted else 0, padx=15, pady=10, font=("Helvetica", 10, "bold"), cursor="hand2")

    def make_edit_panel(self, parent: tk.Widget) -> tk.Frame:
        panel = tk.Frame(parent, bg="white", padx=15, pady=12, highlightthickness=1, highlightbackground="#E2E8F0")
        tk.Label(panel, text="Mark / update", bg="white", fg=NAVY, font=("Helvetica", 12, "bold")).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 9))
        tk.Label(panel, text="Student", bg="white", fg=MUTED, font=("Helvetica", 9)).grid(row=1, column=0, sticky="w", padx=(0, 7))
        self.student_var = tk.StringVar()
        self.student_combo = ttk.Combobox(panel, textvariable=self.student_var, state="readonly", width=23)
        self.student_combo.grid(row=1, column=1, sticky="ew", padx=(0, 14))
        tk.Label(panel, text="Status", bg="white", fg=MUTED, font=("Helvetica", 9)).grid(row=1, column=2, sticky="w", padx=(0, 7))
        self.status_var = tk.StringVar(value="Present")
        self.status_combo = ttk.Combobox(panel, textvariable=self.status_var, values=("Present", "Absent"), state="readonly", width=10)
        self.status_combo.grid(row=1, column=3, sticky="w")
        self.primary_button(panel, "Save encrypted", self.save_attendance).grid(row=2, column=0, columnspan=4, sticky="ew", pady=(12, 0))
        panel.grid_columnconfigure(1, weight=1)
        return panel

    def refresh_records(self) -> None:
        try:
            records = self.store.load()
        except (OSError, ValueError, json.JSONDecodeError) as error:
            messagebox.showerror("Could not load attendance", str(error), parent=self.root)
            return
        for item in self.table.get_children():
            self.table.delete(item)
        self.student_choices.clear()
        total_present = 0
        total_absent = 0
        options = []
        for student in records:
            choice = f"{student['student_id']} · {student['name']}"
            options.append(choice)
            self.student_choices[choice] = student["student_id"]
            for entry in student.get("attendance", []):
                status = entry.get("status", "")
                self.table.insert("", "end", values=(student["student_id"], student["name"], entry.get("date", ""), status, entry.get("updated_at", "")), tags=(status,))
            latest = max(student.get("attendance", []), key=lambda entry: entry.get("date", ""), default=None)
            if latest and latest.get("status") == "Present":
                total_present += 1
            elif latest and latest.get("status") == "Absent":
                total_absent += 1
        self.student_combo.configure(values=options)
        if options and self.student_var.get() not in options:
            self.student_var.set(options[0])
        self.update_stat_cards(len(records), total_present, total_absent)

    def update_stat_cards(self, total: int, present: int, absent: int) -> None:
        for child in self.stats_frame.winfo_children():
            child.destroy()
        summaries = (("STUDENTS", total, NAVY), ("LATEST PRESENT", present, GREEN), ("LATEST ABSENT", absent, RED))
        for index, (label, value, color) in enumerate(summaries):
            card = tk.Frame(self.stats_frame, bg="white", padx=17, pady=12, highlightthickness=1, highlightbackground="#E2E8F0")
            card.pack(side="left", fill="x", expand=True, padx=(0 if index == 0 else 10, 0))
            tk.Label(card, text=label, bg="white", fg=MUTED, font=("Helvetica", 9, "bold")).pack(anchor="w")
            tk.Label(card, text=str(value), bg="white", fg=color, font=("Helvetica", 22, "bold")).pack(anchor="w", pady=(2, 0))

    def save_attendance(self) -> None:
        student_id = self.student_choices.get(self.student_var.get())
        status = self.status_var.get()
        if not student_id:
            messagebox.showerror("Choose a student", "Select a student from the list.", parent=self.root)
            return
        try:
            self.store.mark_attendance(student_id, status)
            self.refresh_records()
            messagebox.showinfo("Attendance saved", f"{student_id} marked {status}. The updated file is encrypted.", parent=self.root)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            messagebox.showerror("Could not save attendance", str(error), parent=self.root)

    def verify_integrity(self) -> None:
        if self.store.verify_file():
            messagebox.showinfo("Integrity verified", "Attendance envelope HMAC is valid. The file passed the integrity check.", parent=self.root)
        else:
            messagebox.showerror("Integrity check failed", "Attendance data is invalid or has been modified. Do not trust the file.", parent=self.root)

    def run_tampering_demo(self) -> None:
        try:
            success = self.store.tampering_demo()
        except (OSError, ValueError, json.JSONDecodeError) as error:
            messagebox.showerror("Demo could not run", str(error), parent=self.root)
            return
        if success:
            messagebox.showinfo(
                "Tampering detected",
                "=== TAMPERING DETECTION DEMO ===\n\n"
                "Original attendance file: Valid\n"
                "Creating temporary test copy...\n"
                "Simulating unauthorized modification...\n"
                "Checking HMAC...\n\n"
                "RESULT: TAMPERING DETECTED!\n"
                "Modified attendance data rejected.\n\n"
                "Checking original file...\n"
                "Original file: VALID",
                parent=self.root,
            )
        else:
            messagebox.showerror("Demo failed", "The modified copy was not rejected or the original file no longer verifies.", parent=self.root)

    def show_test_runner(self) -> None:
        window = tk.Toplevel(self.root)
        window.title("SecureAttendance · Security Test Suite")
        window.geometry("760x540")
        window.minsize(620, 420)
        window.configure(bg=PAGE)

        header = tk.Frame(window, bg=NAVY, padx=22, pady=16)
        header.pack(fill="x")
        tk.Label(header, text="AUTOMATED SECURITY CHECKS", bg=NAVY, fg="#8DE0D1", font=("Helvetica", 9, "bold")).pack(anchor="w")
        tk.Label(header, text="Run the project test suite", bg=NAVY, fg="white", font=("Helvetica", 18, "bold")).pack(anchor="w", pady=(4, 0))

        tk.Label(
            window,
            text="Checks password hashing, encryption, wrong-key rejection, HMAC integrity, status validation, and safe tampering detection. Tests use temporary data and do not change your attendance file.",
            bg=PAGE,
            fg=INK,
            justify="left",
            wraplength=700,
            padx=22,
            pady=14,
            font=("Helvetica", 10),
        ).pack(anchor="w", fill="x")

        output = tk.Text(window, wrap="word", height=16, font=("Menlo", 10), bg="#101B2D", fg="#E4ECF7", insertbackground="white", relief="flat", padx=14, pady=12)
        output.pack(fill="both", expand=True, padx=22, pady=(0, 12))
        output.insert("1.0", "Ready. Choose ‘Run tests’ to execute all automated checks.\n")
        output.configure(state="disabled")
        controls = tk.Frame(window, bg=PAGE)
        controls.pack(fill="x", padx=22, pady=(0, 18))
        status = tk.Label(controls, text="", bg=PAGE, fg=MUTED, font=("Helvetica", 10, "bold"))
        status.pack(side="left")

        def display(text: str) -> None:
            output.configure(state="normal")
            output.delete("1.0", tk.END)
            output.insert("1.0", text)
            output.see(tk.END)
            output.configure(state="disabled")

        def finish(report: str, passed: bool) -> None:
            if not window.winfo_exists():
                return
            display(report)
            status.configure(text="Passed" if passed else "Needs attention", fg=GREEN if passed else RED)
            run_button.configure(state="normal")

        def run_suite() -> None:
            run_button.configure(state="disabled")
            status.configure(text="Running…", fg=TEAL)
            display("Running the security tests with this app's Python environment…\n")

            def worker() -> None:
                try:
                    result = subprocess.run(
                        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
                        cwd=BASE_DIR,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    report = result.stdout + result.stderr
                    if not report:
                        report = "The test runner returned no output.\n"
                    passed = result.returncode == 0
                    summary = "\nRESULT: ALL TESTS PASSED\n" if passed else f"\nRESULT: TESTS FAILED (exit code {result.returncode})\n"
                except (OSError, subprocess.TimeoutExpired) as error:
                    passed = False
                    report = f"Could not finish the test run: {error}\n"
                    summary = "\nRESULT: TEST RUN DID NOT COMPLETE\n"
                self.root.after(0, lambda: finish(report + summary, passed))

            threading.Thread(target=worker, daemon=True).start()

        run_button = self.primary_button(controls, "Run tests", run_suite)
        run_button.pack(side="right")


def main() -> None:
    root = tk.Tk()
    SecureAttendanceApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
