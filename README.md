# SecureAttendance

**Team 3 – Crusaders** · Innovation Hub, Dr. A.P.J. Abdul Kalam Technical University, Lucknow  
**Hackathon:** Build It Secure

SecureAttendance is a small local web app for recording bootcamp attendance safely. The instructor uses the browser UI to sign in, manage attendance, verify file integrity, and demonstrate the security protections.

## The three problems this project solves

1. **Unauthorized attendance edits:** only a signed-in instructor can update a record. Changes to the saved encrypted file are detected.
2. **Private attendance being read:** records are not returned before sign-in and are encrypted on disk.
3. **Guessable instructor passwords:** passwords are stored as salted Argon2id hashes, not plain text. Login allows three attempts per session.

## Temporary demo login

On a **fresh clone** with no existing account, the app asks you to create the first Admin account. For a temporary hackathon demo, enter:

| Field | Demo value |
| --- | --- |
| Username | `demo-admin` |
| Password | `SecureAttendDemo2026!` |

Enter the password again when asked to confirm it. This account is **not pre-created or hardcoded in the application**; the registration screen stores only its Argon2id hash. The demo values are public by design, so use them only with fictional sample data. Never reuse them for a real account. If this project already has an account, use the username and password you previously chose; the hash cannot be reversed to recover that password.

Because these demo credentials are printed here, they are not secret and must not be used to claim that this particular account is unguessable. They let a judge enter the temporary demo. To demonstrate password storage protection, create an additional Instructor account with a private password, then show that the account file stores only its salted hash. Argon2id protects stored hashes; it cannot make a public or weak password secret.

The Admin can create Instructor accounts from **Instructor accounts** in the browser sidebar. Instructors can work with attendance and run the security demonstrations, but cannot create accounts.

## Install and run after cloning from GitHub

The project uses Python 3.10 or newer. The React UI is already bundled in the repository, so Node.js is not needed to run the showcase. Python packages are installed once after cloning; after that, the whole browser application starts with one command.

Replace `YOUR-USERNAME/YOUR-REPOSITORY` below with the GitHub repository address after the project is uploaded.

### macOS or Linux

```bash
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git SecureAttendance
cd SecureAttendance
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
./.venv/bin/python run_showcase.py
```

### Windows PowerShell

```powershell
git clone https://github.com/YOUR-USERNAME/YOUR-REPOSITORY.git SecureAttendance
cd SecureAttendance
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe run_showcase.py
```

The last command starts a local server and opens the browser. Keep that terminal window open while presenting; press **Ctrl+C** to stop the server. The app listens on `127.0.0.1`, so it is for a demonstration on one computer, not for sharing over a network.

### Start it later with one command

After the install step, from the project folder:

- macOS or Linux: `./.venv/bin/python run_showcase.py`
- Windows: `.\.venv\Scripts\python.exe run_showcase.py`

## Fictional test data

On first setup, the application creates these sample records with **Absent** attendance for the current date:

| Student ID | Name | Initial status |
| --- | --- | --- |
| S101 | Aditi Sharma | Absent |
| S102 | Rahul Verma | Absent |
| S103 | Neha Singh | Absent |

These names are fictional demo data. Attendance updates are saved to `data/attendance.enc`; the program does not create a plaintext attendance JSON or CSV file. `data/` and `secrets/` are excluded by `.gitignore`. A new GitHub clone has no keys or attendance file, so the browser shows first-time Admin registration.

## How the secure record system works

### Authentication and account roles

The browser asks for a username and password before showing any attendance. `auth.py` checks the password using Argon2id. Each account gets a random salt, and only the resulting password hash is stored in `secrets/instructor.json`.

The first account has the **Admin** role and can create Instructor accounts. The server checks permissions on protected actions; hiding the account-management page in the browser is not the only access control. Students are not given accounts or attendance-write permissions.

An account created by an earlier version of the project, which stored only one username and hash, is accepted as Admin so its existing login continues to work.

### Confidentiality

`attendance_store.py` serializes records in memory and `crypto_utils.py` encrypts them with AES-256-GCM before saving. Every save uses a fresh random 12-byte nonce. The separate encryption key is stored in `secrets/encryption.key`. Without authentication, the browser API does not return attendance records; reading `data/attendance.enc` reveals an encrypted envelope rather than student names and statuses.

### Integrity

`crypto_utils.py` computes HMAC-SHA256 over a canonical envelope containing the version, nonce, and ciphertext. It checks the HMAC with `hmac.compare_digest` **before** decryption. A separate key is stored in `secrets/hmac.key`. AES-GCM also authenticates the ciphertext; the additional HMAC explicitly demonstrates the hackathon requirement. The **Verify integrity** action checks the saved envelope. **Tampering demo** changes one character in a temporary copy, shows HMAC rejection, deletes that copy, and checks that the original remains valid.

### Key handling

Keys are random, separate from attendance, and never printed by the app. If a key goes missing, the app reports an error instead of generating a replacement that could not decrypt existing records. Local key files are for this educational prototype; production software should use a protected OS key store or dedicated key-management service.

## Demonstration: evidence for each claim

### 1. A student cannot change Absent to Present

1. Sign out and show that the sign-in page does not display the attendance table.
2. Sign in with the Admin or an Instructor account and mark a sample student Present. This shows that an authorized instructor can record attendance.
3. Sign out again. A student has no account or instructor role to authenticate with, and the attendance-update API requires an authenticated session with the `attendance:mark` permission. An unauthenticated request is rejected by the server.
4. Run the test suite to show that only supported attendance statuses are accepted and that modified saved ciphertext fails integrity verification.

### 2. A student cannot read other students' private attendance

1. Sign out and show that the browser displays only the login page, not the records.
2. Explain that the `/api/records` route requires an authenticated session with `attendance:view` permission.
3. Open `data/attendance.enc` in a text editor if you want to show the stored file: it contains the encrypted envelope, not readable student names or statuses. Do not open or share files in `secrets/`.
4. Run the encryption test to show that the attendance can be decrypted with the correct test key and not with an incorrect key.

### 3. A student cannot guess the instructor password from storage

1. Show a failed login attempt; the UI rejects the password and allows at most three attempts in that session.
2. Explain that `secrets/instructor.json` contains the username, role, and Argon2id password hash—not the password. Argon2id hashes are salted and are not decrypted during login.
3. Run the password tests: the correct password is accepted, an incorrect password is rejected, and the stored account file does not contain the plaintext test password.

## Run the tests in the browser UI

After signing in, choose **Security test suite** in the sidebar. The browser shows each test result. Tests use temporary directories and generated test keys, so they do not change the real demo records or keys.

The suite covers:

| Test coverage | Evidence shown |
| --- | --- |
| Password authentication | Correct and incorrect password results; plaintext password is absent from the saved account data. |
| RBAC and account creation | Admin creates an Instructor; Instructor cannot create accounts; duplicate usernames are rejected; old single-account files remain usable as Admin. |
| Encryption | Correct key decrypts test data; wrong key fails; saved attendance envelope does not expose sample names. |
| Integrity | Valid HMAC passes; modified ciphertext and modified HMAC fail. |
| Attendance validation | Only Present and Absent statuses are accepted. |
| Tampering demo | Modified temporary copy is rejected; the original file remains unchanged, valid, and usable. |

The optional terminal command is `./.venv/bin/python -m unittest discover -s tests -v` (Windows: `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`).

## Project files

```text
SecureAttendance/
├── run_showcase.py        # local server and browser app
├── main.py                # optional terminal fallback
├── auth.py                # Argon2id accounts and RBAC
├── crypto_utils.py        # AES-GCM and HMAC operations
├── attendance_store.py    # encrypted attendance storage
├── requirements.txt
├── web/                   # React source and local bundled UI
├── tests/                 # unittest security checks
├── data/                  # generated encrypted attendance
└── secrets/               # generated keys and account hashes; never commit
```

## Prototype limits

- This is a single-computer educational demo. Anyone who can access both local key files and attendance can decrypt or forge records.
- File permissions depend on the operating system. `.gitignore` helps prevent accidental commits but is not a secure backup system.
- RBAC has Admin and Instructor roles; there is no account suspension, audit log, key rotation, or recovery process.
- HMAC shows that the data matches someone holding the integrity key. It does not identify which individual instructor changed the data.
