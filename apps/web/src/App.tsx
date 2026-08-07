import { useState, type FormEvent } from "react";
import {
  createWorkspace,
  listWorkspaces,
  login,
  signup,
} from "./api";
import LumoraDashboard from "./LumoraDashboard";

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
        <div className="auth-brand__logo"><span>L</span>Lumora</div>
        <div>
          <p className="page-kicker">Mission Control</p>
          <h1>Run your content operation with clarity.</h1>
          <p>
            One calm, intelligent workspace for every pipeline, worker,
            customer and Human Review Gate.
          </p>
        </div>
        <div className="auth-signal">
          <span><i /> Live operations</span>
          <span>Secure workspace access</span>
        </div>
      </section>
      <section className="auth-panel">
        <form className="auth-form" onSubmit={(e) => void authenticate("login", e)}>
          <header>
            <p className="page-kicker">Welcome back</p>
            <h2>Sign in to Lumora</h2>
            <span>Enter your workspace credentials to continue.</span>
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
              minLength={8}
              autoComplete="current-password"
            />
          </label>
          <label className="auth-workspace">
            Workspace name (used on first signup)
            <input
              value={workspaceName}
              onChange={(e) => setWorkspaceName(e.target.value)}
              maxLength={200}
            />
          </label>
          <div className="auth-actions">
            <button className="button button--primary" type="submit" disabled={busy}>
              {busy ? "Signing in…" : "Sign in"}
            </button>
            <button
              className="auth-create"
              type="button"
              disabled={busy}
              onClick={(e) => void authenticate("signup", e as unknown as FormEvent)}
            >
              New to Lumora? Create an account
            </button>
          </div>
          {error ? <p className="error" role="alert">{error}</p> : null}
        </form>
        <footer>Protected by workspace-scoped access controls.</footer>
      </section>
    </div>
  );
}
