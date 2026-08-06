import { useState, type FormEvent } from "react";
import {
  createWorkspace,
  listWorkspaces,
  login,
  signup,
} from "./api";
import OperationsDashboard from "./OperationsDashboard";

type Session = {
  token: string;
  workspaceId: string;
  email: string;
};

const STORAGE_KEY = "co.reviewDesk.session";

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
      <OperationsDashboard
        token={session.token}
        workspaceId={session.workspaceId}
        email={session.email}
        onSignOut={() => {
          sessionStorage.removeItem(STORAGE_KEY);
          setSession(null);
        }}
      />
    );
  }

  return (
    <div className="desk">
      <header className="desk__header">
        <p className="desk__brand">Lumora</p>
        <h1>Operations Dashboard</h1>
        <p className="desk__lede">
          Sign in with a workspace admin account to inspect live operations.
        </p>
      </header>

      <form className="panel" onSubmit={(e) => void authenticate("login", e)}>
          <h2>Sign in</h2>
          <label>
            Email
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
          <label>
            Workspace name (used on first signup)
            <input
              value={workspaceName}
              onChange={(e) => setWorkspaceName(e.target.value)}
              maxLength={200}
            />
          </label>
          <div className="queue__actions">
            <button type="submit" disabled={busy}>
              Log in
            </button>
            <button
              type="button"
              disabled={busy}
              onClick={(e) => void authenticate("signup", e as unknown as FormEvent)}
            >
              Create account
            </button>
          </div>
      </form>

      {error ? <p className="error" role="alert">{error}</p> : null}
    </div>
  );
}
