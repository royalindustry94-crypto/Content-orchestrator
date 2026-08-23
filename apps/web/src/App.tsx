import { useState, type FormEvent } from "react";
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

export default function App() {
  const [session, setSession] = useState<Session | null>(() => loadSession());
  const [mode, setMode] = useState<"login" | "signup">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [workspaceName, setWorkspaceName] = useState("My Agency Desk");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function authenticate(mode: "login" | "signup", event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const auth =
        mode === "signup"
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
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      setSession(next);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Authentication failed");
    } finally {
      setBusy(false);
    }
  }

  if (session) {
    return (
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
          setSession(null);
        }}
      />
    );
  }

  return (
    <div className="auth-shell">
      <section className="auth-brand">
        <div className="auth-brand__identity">
          <BusinessManagerMark className="auth-brand__mark" />
          <div>
            <p className="auth-brand__name">The Business Manager</p>
            <span className="auth-brand__section">Command Center</span>
          </div>
        </div>
        <div>
          <p className="page-kicker">Founder workspace access</p>
          <h1>See it. Plan it. Grow it.</h1>
          <p>
            A secure operating system for your content pipeline, workforce,
            and Human Review Gate.
          </p>
        </div>
        <div className="auth-signal">
          <span>Secure workspace access</span>
        </div>
      </section>
      <section className="auth-panel">
        <form className="auth-form" onSubmit={(e) => void authenticate(mode, e)}>
          <header>
            <p className="page-kicker">{mode === "login" ? "Welcome back" : "Get started"}</p>
            <h2>{mode === "login" ? "Sign in to The Business Manager" : "Create your Business Manager account"}</h2>
            <span>
              {mode === "login"
                ? "Enter your credentials to continue."
                : "Set up your account and first workspace."}
            </span>
          </header>
          <label>
            Work email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="username"
            />
          </label>
          <label>
            Password
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
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
                onChange={(e) => setWorkspaceName(e.target.value)}
                maxLength={200}
                required
                placeholder="e.g. Acme Content Team"
              />
            </label>
          ) : null}
          <div className="auth-actions">
            <button className="button button--primary" type="submit" disabled={busy}>
              {busy
                ? mode === "login"
                  ? "Signing in…"
                  : "Creating account…"
                : mode === "login"
                  ? "Sign in"
                  : "Create account"}
            </button>
            <button
              className="auth-create"
              type="button"
              disabled={busy}
              onClick={() => {
                setError(null);
                setMode((current) => (current === "login" ? "signup" : "login"));
              }}
            >
              {mode === "login"
                ? "New here? Create an account"
                : "Already have an account? Sign in"}
            </button>
          </div>
          {error ? <p className="error" role="alert">{error}</p> : null}
        </form>
        <footer>Protected by workspace-scoped access controls.</footer>
      </section>
    </div>
  );
}
