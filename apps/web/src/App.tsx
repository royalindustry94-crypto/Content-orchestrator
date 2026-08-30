import { useEffect, useState, type FormEvent } from "react";
import {
  createWorkspace,
  listWorkspaces,
  login,
  signup,
} from "./api";
import LumoraDashboard from "./LumoraDashboard";
import { BusinessManagerMark } from "./BusinessManagerMark";

type Session = {
  token: string;
  workspaceId: string;
  email: string;
};

const STORAGE_KEY = "lumora.missionControl.session";
const AUTO_PREVIEW_SESSION = import.meta.env.VITE_FOUNDER_TEST_AUTO_LOGIN === "true";

function loadSession(): Session | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Session;
    if (!parsed.token || !parsed.workspaceId) return null;
    return parsed;
  } catch {
    return null;
  }
}

function disposablePreviewCredentials() {
  const random = new Uint32Array(4);
  window.crypto.getRandomValues(random);
  const suffix = Array.from(random, (value) => value.toString(16).padStart(8, "0")).join("");
  return {
    email: `founder-test-${Date.now()}-${suffix.slice(0, 12)}@example.com`,
    password: `Preview!Aa7-${suffix}-${Date.now()}`,
  };
}

export default function App() {
  const [session, setSession] = useState<Session | null>(() => loadSession());
  const [launchState, setLaunchState] = useState<"hidden" | "visible" | "exiting">(() => loadSession() ? "visible" : "hidden");
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [workspaceName, setWorkspaceName] = useState("My Agency Desk");
  const [error, setError] = useState<string | null>(null);
  const [recoveryNotice, setRecoveryNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [previewBootstrapState, setPreviewBootstrapState] = useState<"idle" | "running" | "failed">("idle");

  useEffect(() => {
    if (!session || launchState !== "visible") return;
    const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (reduceMotion) {
      setLaunchState("hidden");
      return;
    }
    const frame = window.requestAnimationFrame(() => setLaunchState("exiting"));
    const timeout = window.setTimeout(() => setLaunchState("hidden"), 420);
    return () => {
      window.cancelAnimationFrame(frame);
      window.clearTimeout(timeout);
    };
  }, [launchState, session]);

  useEffect(() => {
    if (!AUTO_PREVIEW_SESSION || session || previewBootstrapState !== "idle") return;

    setPreviewBootstrapState("running");
    setError(null);
    const credentials = disposablePreviewCredentials();

    void (async () => {
      try {
        const auth = await signup(credentials.email, credentials.password);
        const existing = await listWorkspaces(auth.access_token);
        let workspaceId = existing[0]?.id;
        if (!workspaceId) {
          const created = await createWorkspace(auth.access_token, "Founder Test Workspace");
          workspaceId = created.id;
        }
        const next: Session = {
          token: auth.access_token,
          workspaceId,
          email: auth.email,
        };
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
        setLaunchState("visible");
        setSession(next);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Preview session could not start");
        setPreviewBootstrapState("failed");
      }
    })();
  }, [previewBootstrapState, session]);

  async function authenticate(nextMode: "login" | "signup", event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setRecoveryNotice(null);
    try {
      const auth =
        nextMode === "signup"
          ? await signup(email.trim(), password)
          : await login(email.trim(), password);
      const existing = await listWorkspaces(auth.access_token);
      let workspaceId = existing[0]?.id;
      if (!workspaceId) {
        const created = await createWorkspace(
          auth.access_token,
          workspaceName.trim() || "My Agency Desk",
        );
        workspaceId = created.id;
      }
      const next: Session = {
        token: auth.access_token,
        workspaceId,
        email: auth.email,
      };
      // Tokens live only in this browser tab. The preview does not persist passwords
      // or claim refresh-token, device-management, or revocation support it lacks.
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      setLaunchState("visible");
      setSession(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  if (session) {
    return (
      <>
        <LumoraDashboard
          token={session.token}
          workspaceId={session.workspaceId}
          email={session.email}
          onWorkspaceChange={(workspaceId) => {
            const next = { ...session, workspaceId };
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
            setSession(next);
          }}
          onSignOut={() => {
            sessionStorage.removeItem(STORAGE_KEY);
            setLaunchState("hidden");
            setSession(null);
            if (AUTO_PREVIEW_SESSION) setPreviewBootstrapState("idle");
          }}
        />
        {launchState !== "hidden" ? (
          <div aria-label="The Business Manager launch" className={launchState === "exiting" ? "business-launch business-launch--exiting" : "business-launch"} role="status">
            <BusinessManagerMark className="business-launch__mark" />
            <p>The Business Manager</p>
            <span>We get it sorted.</span>
          </div>
        ) : null}
      </>
    );
  }

  if (AUTO_PREVIEW_SESSION) {
    return (
      <main className="auth-shell auth-shell--approved">
        <section className="auth-card" aria-live="polite">
          <div className="auth-lockup" aria-label="The Business Manager — Founder Test Preview">
            <BusinessManagerMark className="auth-lockup__mark" />
            <strong className="auth-lockup__name">The Business Manager</strong>
            <small className="auth-lockup__subtitle">Founder Test Preview</small>
          </div>
          {previewBootstrapState === "failed" ? (
            <div className="auth-form auth-form--approved">
              <h1>Preview could not start</h1>
              {error ? <p className="error" role="alert">{error}</p> : null}
              <button
                className="button button--primary auth-submit"
                type="button"
                onClick={() => setPreviewBootstrapState("idle")}
              >
                RETRY TEST SESSION
              </button>
            </div>
          ) : (
            <div className="auth-form auth-form--approved" role="status">
              <h1>Preparing test workspace…</h1>
              <p className="auth-notice">Creating a disposable test session. No login is required for this preview.</p>
            </div>
          )}
        </section>
      </main>
    );
  }

  return (
    <main className="auth-shell auth-shell--approved">
      <section className="auth-card" aria-labelledby="auth-title">
        <div className="auth-lockup" aria-label="The Business Manager — Business Operating System">
          <BusinessManagerMark className="auth-lockup__mark" />
          <strong className="auth-lockup__name">The Business Manager</strong>
          <small className="auth-lockup__subtitle">Business Operating System</small>
        </div>
        <form className="auth-form auth-form--approved" onSubmit={(event) => void authenticate(mode, event)}>
          <h1 id="auth-title">{mode === "login" ? "Sign in" : "Create account"}</h1>
          <label>
            Email address
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              autoComplete="username"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              minLength={mode === "signup" ? 12 : 1}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
            />
          </label>
          {mode === "signup" ? (
            <label className="auth-workspace">
              Workspace name
              <input
                value={workspaceName}
                onChange={(event) => setWorkspaceName(event.target.value)}
                maxLength={200}
                required
                placeholder="e.g. Acme Content Team"
              />
            </label>
          ) : null}
          {mode === "login" ? (
            <div className="auth-security-row">
              <label className="auth-remember" title="Secure persistent sessions are not configured for this disposable preview.">
                <input type="checkbox" disabled />
                <span>Remember me <small>Unavailable in preview</small></span>
              </label>
              <button
                className="auth-link"
                type="button"
                onClick={() => setRecoveryNotice("Password recovery is not configured for this disposable preview.")}
              >
                Forgot password?
              </button>
            </div>
          ) : null}
          <button className="button button--primary auth-submit" type="submit" disabled={busy}>
            {busy ? (mode === "login" ? "Signing in…" : "Creating account…") : mode === "login" ? "SIGN IN" : "CREATE ACCOUNT"}
          </button>
          <button
            className="auth-create"
            type="button"
            disabled={busy}
            onClick={() => {
              setError(null);
              setRecoveryNotice(null);
              setMode((current) => (current === "login" ? "signup" : "login"));
            }}
          >
            {mode === "login" ? "New to The Business Manager? Create account" : "Already have an account? Sign in"}
          </button>
          {recoveryNotice ? <p className="auth-notice" role="status">{recoveryNotice}</p> : null}
          {error ? <p className="error" role="alert">{error}</p> : null}
        </form>
      </section>
    </main>
  );
}