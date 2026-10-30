./.venv-mac/bin/python run_showcase.py

# SecureAttendance

**Team 3 – Crusaders** · Innovation Hub, Dr. A.P.J. Abdul Kalam Technical University, Lucknow  
**Hackathon:** Build It Secure

SecureAttendance is a beginner-friendly local browser application for protecting a bootcamp's attendance records. It demonstrates password hashing, encryption at rest, and detection of unauthorized changes using real cryptographic libraries. The presenter uses the browser UI for registration, login, attendance changes, security demonstrations, and the automated test suite.

## Problem statement

A participant changed an Absent entry to Present, read other students' private records, and guessed an instructor password that had been stored as plain text. This application restricts record access to an authenticated instructor, encrypts saved data, and checks its integrity before trusting it.

## Objectives

- Authenticate the instructor without storing a plain-text password.
- Keep attendance confidential while it is saved on disk.
- Detect edits to the encrypted attendance file.
- Keep the program small enough to explain during a college hackathon.

## Technologies, in plain language

- **Argon2id (`argon2-cffi`)** turns the instructor password into a one-way password hash. Each registration gets a random salt automatically. The salt is stored as part of the encoded hash and means equal passwords do not produce equal stored strings. Login checks a candidate password against the hash; it does not decrypt a password.
- **AES-256-GCM (`cryptography`)** encrypts attendance with a 256-bit key and also authenticates the ciphertext. Confidentiality means someone who only reads the file cannot read names and statuses. Each save creates a fresh random 12-byte **nonce**. A nonce is a one-time value for a given AES-GCM key; reusing it can break security.
- **HMAC-SHA256** uses a separate random 256-bit secret key to authenticate a canonical JSON representation of the envelope's version, nonce, and ciphertext. The program calls `hmac.compare_digest` and rejects invalid data before decrypting. AES-GCM already provides authenticated encryption; this additional HMAC is included to clearly demonstrate the hackathon's HMAC requirement. A valid HMAC shows possession of the integrity key, not which individual instructor made the record.

Three security goals are different:

- **Authentication:** prove the instructor's identity by checking their password hash.
- **Confidentiality:** prevent unauthorized readers from understanding saved attendance using encryption.
- **Integrity:** detect unauthorized changes using HMAC verification (and AES-GCM's own tag).

## Architecture and data flow

`run_showcase.py` starts a local-only Python HTTP server and opens the React interface in the browser. The server handles registration, login, encrypted attendance changes, integrity checks, the temporary-copy tampering demo, and the automated tests. React runs locally from the bundled `web/assets/app.js`; it does not need a separate development server or internet connection. `main.py` remains available as a terminal fallback. `auth.py` stores and checks the Argon2id hash. `attendance_store.py` reads and writes attendance. `crypto_utils.py` generates/loads keys and performs encryption, decryption, and HMAC verification.

When the instructor saves an update, the app serializes the records in memory, encrypts them with AES-GCM and a new nonce, computes HMAC over the canonical envelope, then writes only the encrypted envelope to `data/attendance.enc`. When reading, it verifies HMAC first and only then decrypts. No plaintext JSON or CSV attendance file is created. The only unencrypted files contain the instructor username/hash and cryptographic keys; they are protected from Git and have restrictive permissions where supported.

## Folder structure

```text
SecureAttendance/
├── main.py
├── run_showcase.py        # start the one-command browser showcase
├── auth.py
├── crypto_utils.py
├── attendance_store.py
├── requirements.txt
├── README.md
├── .gitignore
├── web/
│   ├── index.html
│   ├── src/main.jsx        # React interface source
│   ├── src/styles.css
│   ├── assets/app.js       # bundled React app, served locally
│   ├── package.json
│   └── package-lock.json
├── data/                 # generated encrypted attendance file
├── secrets/              # generated keys and instructor hash; never commit
└── tests/
    └── test_secureattendance.py
```

The `data/` and `secrets/` files are generated on first run. Do not add them to version control. `.gitignore` excludes their contents. Local key-file storage is suitable only for this educational prototype. Production software should use a protected operating-system key store or a dedicated key-management service, with access control, backups, rotation, and recovery procedures.

## Install and run (macOS)

Open Terminal in the `SecureAttendance` folder. These instructions use the Python 3.15 already installed on this Mac. The project constrains `cryptography` to the 44.x release line because it provides a prebuilt macOS wheel usable by this Python, so pip does not need to compile it or find system OpenSSL development files. Do this setup once:

```bash
python3 --version
python3 -m venv .venv-mac
source .venv-mac/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

You already created `.venv-mac` and installed the dependencies. The command to start the complete browser showcase is:

```bash
./.venv-mac/bin/python run_showcase.py
```

That is the only terminal command needed for a demonstration. It starts the local server and opens the browser. Keep that terminal window open while presenting; press Ctrl+C there when the demo is over. No Node.js command is needed at runtime. The commands `py` and `.venv\\Scripts\\Activate.ps1` are Windows-only and do not work in macOS zsh.

The first run asks you to create a username and enter a password twice. Password input is hidden. Choose at least 10 characters. Registration generates the AES and HMAC keys and creates fictional sample students S101, S102, and S103 with Absent attendance for today. The app then presents the login screen.

## Browser showcase

The React interface provides the complete instructor workflow:

1. Register the instructor on first use, or sign in with the existing account. Passwords are sent only to the local server and are stored as Argon2id hashes.
2. View the student register after authentication. Use each row's **Present** or **Absent** button to save an encrypted attendance update.
3. Choose **Verify integrity** to check the saved HMAC.
4. Choose **Tampering demo** to alter a temporary copy, show that verification rejects it, then confirm the original file still verifies.
5. Choose **Security test suite** or **Run test suite** to run all `unittest` checks and display the individual results in the browser.
6. Sign out from the left sidebar. Three failed login attempts end the login session; restart the showcase command to begin a fresh session.

The server binds to `127.0.0.1`, so this prototype is intended for a demonstration on the same computer, not a shared network deployment. The React app and styles are served from local project files. If you edit `web/src/main.jsx`, rebuild the bundled app from the `web/` directory with `npm install` and `npm run build`; normal demo runs do not need npm.

**Keep the `secrets/` directory safe and backed up.** The program never silently regenerates a missing key: that would make existing encrypted records unreadable. If a key is missing, restore the original key from a secure backup. Never print or share the key files.

## Hackathon demonstration

1. Run `./.venv-mac/bin/python run_showcase.py` once. The browser opens to the local React app.
2. Register an instructor in the browser on the first run, then sign in. Attendance stays hidden until sign-in succeeds.
3. Use the **Present** or **Absent** button on a student row to update today's attendance. The dashboard refreshes and shows the new timestamp.
4. Choose **Verify integrity** to show that the saved attendance envelope passes HMAC verification.
5. Choose **Tampering demo** to change one ciphertext character in a temporary copy, show the HMAC rejection, and confirm that the original file remains valid.
6. Choose **Security test suite** to run all automated tests and show each result in the browser UI.
7. Sign out and try an incorrect password. The UI rejects it and ends the login session after three failed attempts.

The demo's success comes from `verify_envelope` checking the modified copy's HMAC with the real secret key; it is not a hardcoded result.

## Automated tests

Run from this folder with the virtual environment active:

```bash
python -m unittest discover -s tests -v
```

Tests use temporary directories and generated test keys, so they do not touch the app's real demo files. The test names show which checks passed. The suite covers:

| Test area | What it checks |
| --- | --- |
| Password authentication | Correct password accepted; wrong password rejected; stored file does not contain the password and contains an Argon2id hash. |
| Encryption | Correct key decrypts attendance; wrong key fails; saved envelope contains no sample student name in plaintext. |
| Integrity | Untouched envelope passes HMAC; changed ciphertext and changed HMAC fail. |
| Input validation | Only `Present` or `Absent` is accepted. |
| Tampering demo | A modified temporary copy is rejected, the original file bytes stay unchanged, the original still verifies, and the temporary copy is removed. |

The automated test suite is available from the browser dashboard. This standalone terminal command is optional:

```bash
./.venv-mac/bin/python -m unittest discover -s tests -v
```

## Security limitations and future improvements

- This is an educational, single-machine prototype; a user with access to both key files and records can decrypt or forge them.
- File permissions are best effort and differ across operating systems. `.gitignore` reduces accidental commits but is not a secure backup or access-control system.
- The HMAC key is stored locally beside the encryption key. A production system should isolate keys in an OS key store/KMS and control which process can use them.
- There is no multi-user role management, audit log, network transport, key rotation, or recovery mechanism. Add these only with a reviewed threat model.
- HMAC proves the data matches a holder of the shared key; it does not provide individual non-repudiation or identify which instructor changed it.

## Judge-friendly explanations

**Why hash passwords instead of encrypting them?** The app needs to check a password, not recover it. A salted Argon2id hash supports verification without storing a reversible password.

**Why encrypt attendance?** Encryption provides confidentiality if someone copies or reads the saved file without the key.

**Why use both AES-GCM and HMAC?** GCM already detects ciphertext changes, while the separate HMAC explicitly demonstrates the requested HMAC integrity check and is verified before decryption.

**Does a valid HMAC prove the instructor changed a record?** No. It proves the envelope was made by someone with the HMAC key. Authentication controls app access, but the shared local key is not a personal signature.
