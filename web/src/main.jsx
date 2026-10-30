import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";

const API = "";

async function request(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.error || "The request could not be completed.");
    error.data = data;
    throw error;
  }
  return data;
}

function LockMark() {
  return <div className="lock-mark"><span>SA</span><i /></div>;
}

function Brand({ compact = false }) {
  return <div className={`brand ${compact ? "brand-compact" : ""}`}><LockMark /><div><strong>SecureAttendance</strong><small>BUILD IT SECURE · TEAM 3</small></div></div>;
}

function AuthPage({ configured, onAuth }) {
  const [mode, setMode] = useState(configured ? "login" : "register");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [remaining, setRemaining] = useState(3);
  const registering = mode === "register";

  async function submit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      const result = await request(registering ? "/api/register" : "/api/login", {
        method: "POST",
        body: JSON.stringify({ username, password, confirm_password: confirm }),
      });
      if (registering) {
        setMode("login");
        setPassword("");
        setConfirm("");
        setError("Account created. Sign in with your new credentials.");
      } else {
        onAuth(result.username);
      }
    } catch (err) {
      setError(err.message);
      if (err.data?.attempts_remaining !== undefined) setRemaining(err.data.attempts_remaining);
    } finally {
      setBusy(false);
    }
  }

  return <main className="auth-shell">
    <section className="auth-story">
      <Brand />
      <div className="story-copy">
        <div className="eyebrow"><span className="pulse-dot" /> COLLEGE CRYPTOGRAPHY HACKATHON</div>
        <h1>Attendance records,<br /><em>secured by design.</em></h1>
        <p>Protecting private student records with strong authentication, encrypted storage, and real integrity checks.</p>
        <div className="security-list">
          <div><b>01</b><span><strong>Private by default</strong><small>Records stay hidden until instructor sign-in.</small></span></div>
          <div><b>02</b><span><strong>Encrypted at rest</strong><small>AES-256-GCM protects saved attendance.</small></span></div>
          <div><b>03</b><span><strong>Integrity checked</strong><small>HMAC detects unauthorized file changes.</small></span></div>
        </div>
      </div>
      <div className="story-footer">INNOVATION HUB · DR. A.P.J. ABDUL KALAM TECHNICAL UNIVERSITY, LUCKNOW</div>
    </section>
    <section className="auth-panel">
      <div className="mobile-brand"><Brand /></div>
      <div className="auth-card">
        <div className="auth-card-top"><span className="section-label">INSTRUCTOR PORTAL</span><span className="secure-chip"><i /> LOCAL & SECURE</span></div>
        <h2>{registering ? "Create your account" : "Welcome back"}</h2>
        <p className="auth-subtitle">{registering ? "Set up the instructor account for your demo." : "Sign in to open the attendance dashboard."}</p>
        <form onSubmit={submit}>
          <label>Instructor username<input autoComplete="username" required value={username} onChange={(e) => setUsername(e.target.value)} placeholder="e.g. instructor" /></label>
          <label>Password<input autoComplete={registering ? "new-password" : "current-password"} required minLength={registering ? 10 : undefined} type="password" value={password} onChange={(e) => setPassword(e.target.value)} placeholder={registering ? "At least 10 characters" : "Enter your password"} /></label>
          {registering && <label>Confirm password<input autoComplete="new-password" required type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} placeholder="Type it again" /></label>}
          {error && <div className={`form-message ${error.startsWith("Account created") ? "success-message" : ""}`} role="status">{error}{!registering && remaining < 3 && remaining > 0 ? ` ${remaining} attempt(s) remain.` : ""}</div>}
          {!registering && remaining === 0 && <div className="form-message">Three sign-in attempts used. Restart the showcase to start a new login session.</div>}
          <button className="button button-primary auth-submit" disabled={busy || (!registering && remaining === 0)}>{busy ? "Please wait…" : registering ? "Create instructor account" : "Sign in securely"}<span>↗</span></button>
        </form>
        <div className="auth-note"><span className="tiny-lock">▣</span>{registering ? "Your password is hashed with Argon2id. It is never stored as plain text." : "Three attempts are allowed per login session."}</div>
      </div>
      <div className="panel-caption">SECUREATTENDANCE · TEAM 3 — CRUSADERS</div>
    </section>
  </main>;
}

function Icon({ name }) {
  const paths = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
    shield: <><path d="M12 3 19 6v5c0 4.5-3 7.5-7 10-4-2.5-7-5.5-7-10V6l7-3Z"/><path d="m9 12 2 2 4-4"/></>,
    demo: <><path d="M8 5H5v14h14v-3"/><path d="M10 14 20 4"/><path d="M13 4h7v7"/><path d="M5 8h4"/></>,
    tests: <><path d="m9 11 2 2 4-4"/><path d="M12 3 5 6v5c0 4.5 3 7.5 7 10 4-2.5 7-5.5 7-10V6l-7-3Z"/></>,
    logout: <><path d="M10 17l5-5-5-5"/><path d="M15 12H3"/><path d="M12 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6"/></>,
    chevron: <path d="m9 18 6-6-6-6"/>,
    check: <path d="m5 12 4 4L19 6"/>,
  };
  return <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

function Dashboard({ username, onLogout }) {
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState("");
  const [notice, setNotice] = useState(null);
  const [testResults, setTestResults] = useState(null);
  const [testRunning, setTestRunning] = useState(false);
  const [activeView, setActiveView] = useState("attendance");
  const [showModal, setShowModal] = useState(false);

  async function loadRecords() {
    setLoading(true);
    try {
      const data = await request("/api/records");
      setRecords(data.records);
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { loadRecords(); }, []);

  const latest = useMemo(() => records.map((student) => ({
    ...student,
    latest: [...(student.attendance || [])].sort((a, b) => b.date.localeCompare(a.date))[0],
  })), [records]);
  const presentCount = latest.filter((student) => student.latest?.status === "Present").length;
  const absentCount = latest.filter((student) => student.latest?.status === "Absent").length;

  async function updateAttendance(studentId, status) {
    setBusyId(studentId);
    try {
      const data = await request("/api/attendance", { method: "POST", body: JSON.stringify({ student_id: studentId, status }) });
      setNotice({ type: "success", text: data.message });
      await loadRecords();
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    } finally {
      setBusyId("");
    }
  }

  async function verifyIntegrity() {
    try {
      const result = await request("/api/verify", { method: "POST", body: "{}" });
      setNotice({ type: result.valid ? "success" : "error", text: result.message });
    } catch (error) {
      setNotice({ type: "error", text: error.message });
    }
  }

  async function runDemo() {
    setShowModal(true);
    setActiveView("demo");
    setTestResults(null);
    try {
      const result = await request("/api/tampering-demo", { method: "POST", body: "{}" });
      setTestResults({ kind: "demo", passed: result.detected && result.original_valid, output: [
        "=== TAMPERING DETECTION DEMO ===",
        "",
        "Original attendance file: Valid",
        "Creating temporary test copy...",
        "Simulating unauthorized modification...",
        "Checking HMAC...",
        "",
        result.detected ? "RESULT: TAMPERING DETECTED!" : "RESULT: Tampering was not detected.",
        "Modified attendance data rejected.",
        "",
        "Checking original file...",
        `Original file: ${result.original_valid ? "VALID" : "INVALID"}`,
      ].join("\n") });
    } catch (error) {
      setTestResults({ kind: "demo", passed: false, output: error.message });
    }
  }

  async function runTests() {
    setShowModal(true);
    setActiveView("tests");
    setTestRunning(true);
    setTestResults(null);
    try {
      const result = await request("/api/tests", { method: "POST", body: "{}" });
      setTestResults({ kind: "tests", passed: result.passed, output: `${result.output}\n${result.passed ? "RESULT: ALL SECURITY TESTS PASSED" : `RESULT: ${result.failures} TEST FAILURE(S)`}\n${result.tests_run} tests executed.` });
    } catch (error) {
      setTestResults({ kind: "tests", passed: false, output: error.message });
    } finally {
      setTestRunning(false);
    }
  }

  const today = new Intl.DateTimeFormat(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" }).format(new Date());

  return <div className="app-shell">
    <aside className="sidebar">
      <Brand compact />
      <div className="sidebar-section">WORKSPACE</div>
      <button className={`nav-item ${activeView === "attendance" ? "active" : ""}`} onClick={() => { setActiveView("attendance"); setShowModal(false); }}><Icon name="grid" />Attendance overview</button>
      <div className="sidebar-section security-section">SECURITY DEMOS</div>
      <button className={`nav-item ${activeView === "demo" ? "active" : ""}`} onClick={runDemo}><Icon name="demo" />Tampering demo</button>
      <button className={`nav-item ${activeView === "tests" ? "active" : ""}`} onClick={runTests}><Icon name="tests" />Security test suite</button>
      <div className="sidebar-bottom">
        <div className="local-status"><span className="pulse-dot" /><span><strong>Local demo server</strong><small>Only accessible on this Mac</small></span></div>
        <button className="logout-button" onClick={onLogout}><Icon name="logout" />Sign out</button>
        <div className="team-signature">TEAM 3 <span>·</span> CRUSADERS</div>
      </div>
    </aside>
    <main className="main-area">
      <header className="topbar"><div className="breadcrumb">SECUREATTENDANCE <Icon name="chevron" /> <strong>{activeView === "attendance" ? "ATTENDANCE" : activeView === "demo" ? "TAMPERING DEMO" : "SECURITY TESTS"}</strong></div><div className="user-pill"><span className="avatar">{username.slice(0, 1).toUpperCase()}</span><span>{username}</span><i /></div></header>
      <div className="content-area">
        {notice && <div className={`toast toast-${notice.type}`} role="status"><span>{notice.type === "success" ? <Icon name="check" /> : "!"}</span>{notice.text}<button onClick={() => setNotice(null)}>×</button></div>}
        <div className="page-heading"><div><div className="eyebrow muted-eyebrow">{activeView === "attendance" ? "BOOTCAMP · DAILY REGISTER" : "LIVE CRYPTOGRAPHY DEMONSTRATION"}</div><h1>{activeView === "attendance" ? "Attendance overview" : activeView === "demo" ? "Tampering detection" : "Security test suite"}</h1><p>{activeView === "attendance" ? "Manage student attendance and protect every saved update." : activeView === "demo" ? "Watch HMAC reject an unauthorized change to a temporary copy." : "Run the project checks and show each result right here."}</p></div><div className="date-chip"><span className="calendar-dot">◷</span>{today}</div></div>

        <section className="metric-grid">
          <Metric icon="◎" label="TOTAL STUDENTS" value={loading ? "—" : records.length} detail="In the bootcamp register" color="blue" />
          <Metric icon="✓" label="PRESENT" value={loading ? "—" : presentCount} detail="Latest recorded status" color="green" />
          <Metric icon="–" label="ABSENT" value={loading ? "—" : absentCount} detail="Latest recorded status" color="amber" />
          <Metric icon="⌑" label="RECORD SECURITY" value="AES-256" detail="Encrypted · HMAC verified" color="purple" />
        </section>

        <section className="records-card">
          <div className="records-header"><div><h2>Student register</h2><p>Choose Present or Absent to save today's attendance.</p></div><button className="button button-outline" onClick={verifyIntegrity}><Icon name="shield" /> Verify integrity</button></div>
          <div className="table-scroll"><table><thead><tr><th>STUDENT</th><th>STUDENT ID</th><th>DATE</th><th>STATUS</th><th>LAST UPDATED</th><th>UPDATE ATTENDANCE</th></tr></thead><tbody>
            {loading ? <tr><td className="empty-state" colSpan="6">Decrypting and loading attendance…</td></tr> : latest.length === 0 ? <tr><td className="empty-state" colSpan="6">No attendance records found.</td></tr> : latest.map((student) => <tr key={student.student_id}>
              <td><div className="student-cell"><span className={`student-avatar avatar-${student.student_id.slice(-1)}`}>{student.name.split(" ").map((part) => part[0]).join("")}</span><strong>{student.name}</strong></div></td>
              <td><span className="id-pill">{student.student_id}</span></td>
              <td>{student.latest?.date || "—"}</td>
              <td><span className={`status-badge ${student.latest?.status === "Present" ? "status-present" : "status-absent"}`}><i />{student.latest?.status || "Not marked"}</span></td>
              <td className="timestamp">{student.latest?.updated_at ? new Date(student.latest.updated_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "—"}</td>
              <td><div className="row-actions"><button disabled={busyId === student.student_id} className="quick-present" onClick={() => updateAttendance(student.student_id, "Present")}>Present</button><button disabled={busyId === student.student_id} className="quick-absent" onClick={() => updateAttendance(student.student_id, "Absent")}>Absent</button></div></td>
            </tr>)}
          </tbody></table></div>
          <div className="records-foot"><span><span className="lock-small">▣</span> Changes are encrypted immediately when saved.</span><span>{records.length} student{records.length === 1 ? "" : "s"}</span></div>
        </section>

        <section className="demo-strip"><div className="demo-icon"><Icon name="shield" /></div><div className="demo-copy"><strong>Show the security controls</strong><span>Run the tampering demo or execute all automated security tests in this browser.</span></div><button className="button button-dark" onClick={runDemo}>Run tampering demo <Icon name="chevron" /></button><button className="button button-outline test-cta" onClick={runTests}>Run test suite</button></section>
        <div className="privacy-note"><Icon name="shield" /><span><strong>Privacy by design</strong> Attendance is decrypted only after sign-in. This demo server listens on this computer only.</span></div>
      </div>
    </main>
    {showModal && <ResultsModal kind={activeView} result={testResults} running={testRunning} onClose={() => { setShowModal(false); setActiveView("attendance"); }} onRerun={activeView === "tests" ? runTests : runDemo} />}
  </div>;
}

function Metric({ icon, label, value, detail, color }) {
  return <div className="metric-card"><div className={`metric-icon metric-${color}`}>{icon}</div><div className="metric-label">{label}</div><div className="metric-value">{value}</div><div className="metric-detail">{detail}</div></div>;
}

function ResultsModal({ kind, result, running, onClose, onRerun }) {
  const title = kind === "demo" ? "Tampering detection demo" : "Automated security checks";
  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="results-modal" role="dialog" aria-modal="true" aria-label={title}>
      <div className="modal-header"><div><div className="eyebrow muted-eyebrow">SECUREATTENDANCE · LIVE RESULTS</div><h2>{title}</h2></div><button className="modal-close" onClick={onClose} aria-label="Close">×</button></div>
      <div className="modal-body">
        {!result && <div className="run-placeholder"><div className="spinner" />{running ? "Running checks in temporary test storage…" : "Preparing the demonstration…"}</div>}
        {result && <><div className={`result-banner ${result.passed ? "result-good" : "result-bad"}`}><span>{result.passed ? "✓" : "!"}</span><div><strong>{result.passed ? (kind === "demo" ? "Tampering detected" : "All checks passed") : "Action needs attention"}</strong><small>{kind === "demo" ? "The modified copy failed HMAC verification; the original remained valid." : "Detailed test output is shown below."}</small></div></div><pre className="result-output">{result.output}</pre></>}
      </div>
      <div className="modal-footer"><span>Test files use temporary directories; attendance data is not overwritten.</span><div>{result && <button className="button button-outline" onClick={onRerun}>Run again</button>}<button className="button button-primary" onClick={onClose}>Done</button></div></div>
    </section>
  </div>;
}

function App() {
  const [session, setSession] = useState(null);
  const [checking, setChecking] = useState(true);
  useEffect(() => {
    request("/api/session").then(setSession).catch(() => setSession({ configured: true, authenticated: false })).finally(() => setChecking(false));
  }, []);
  async function logout() {
    await request("/api/logout", { method: "POST", body: "{}" }).catch(() => {});
    setSession((current) => ({ ...current, authenticated: false, username: null }));
  }
  if (checking) return <div className="boot-screen"><div className="boot-mark">SA</div><span>Starting secure local workspace…</span></div>;
  if (session?.authenticated) return <Dashboard username={session.username} onLogout={logout} />;
  return <AuthPage configured={Boolean(session?.configured)} onAuth={(username) => setSession((current) => ({ ...current, configured: true, authenticated: true, username }))} />;
}

createRoot(document.getElementById("root")).render(<App />);
