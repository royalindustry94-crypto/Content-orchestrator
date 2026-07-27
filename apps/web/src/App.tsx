import { useCallback, useEffect, useState, type FormEvent } from "react";
import {
  createContentJob,
  createWorkspace,
  decideReviewGate,
  listReviewGates,
  listWorkspaces,
  login,
  signup,
  type ReviewGate,
} from "./api";

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
  const [gates, setGates] = useState<ReviewGate[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [topic, setTopic] = useState("");
  const [scriptBody, setScriptBody] = useState("");
  const [notes, setNotes] = useState<Record<string, string>>({});

  const refresh = useCallback(async (active: Session) => {
    setBusy(true);
    setError(null);
    try {
      const rows = await listReviewGates(active.token, active.workspaceId, "awaiting");
      setGates(rows);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load review queue");
      setGates([]);
    } finally {
      setBusy(false);
    }
  }, []);

  useEffect(() => {
    if (session) {
      void refresh(session);
    }
  }, [session, refresh]);

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

  async function submitDraft(event: FormEvent) {
    event.preventDefault();
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      const payload: { topic: string; script_body?: string } = {
        topic: topic.trim(),
      };
      const body = scriptBody.trim();
      if (body) {
        payload.script_body = body;
      }
      await createContentJob(session.token, session.workspaceId, payload);
      setTopic("");
      setScriptBody("");
      await refresh(session);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create content job");
    } finally {
      setBusy(false);
    }
  }

  async function decide(gateId: string, approved: boolean) {
    if (!session) return;
    setBusy(true);
    setError(null);
    try {
      await decideReviewGate(
        session.token,
        session.workspaceId,
        gateId,
        approved,
        notes[gateId]?.trim() || undefined,
      );
      await refresh(session);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Decision failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="desk">
      <header className="desk__header">
        <p className="desk__brand">Content Orchestrator</p>
        <h1>Review Desk</h1>
        <p className="desk__lede">
          Private Beta — every draft stops at the Human Review Gate before publish.
        </p>
      </header>

      {!session ? (
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
      ) : (
        <>
          <div className="desk__meta">
            <span>
              {session.email} · Workspace {session.workspaceId}
            </span>
            <button
              type="button"
              className="linkish"
              onClick={() => {
                sessionStorage.removeItem(STORAGE_KEY);
                setSession(null);
                setGates([]);
              }}
            >
              Sign out
            </button>
          </div>

          <form className="panel" onSubmit={(e) => void submitDraft(e)}>
            <h2>Submit draft for review</h2>
            <label>
              Topic
              <input
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                required
                maxLength={500}
              />
            </label>
            <label>
              Script body (optional — Draft Desk generates if empty)
              <textarea
                value={scriptBody}
                onChange={(e) => setScriptBody(e.target.value)}
                rows={6}
              />
            </label>
            <button type="submit" disabled={busy}>
              Send to Review Gate
            </button>
          </form>

          <section className="panel">
            <div className="panel__row">
              <h2>Awaiting review</h2>
              <button type="button" onClick={() => void refresh(session)} disabled={busy}>
                Refresh
              </button>
            </div>
            {gates.length === 0 ? (
              <p className="muted">No items in the gate.</p>
            ) : (
              <ul className="queue">
                {gates.map((gate) => (
                  <li key={gate.id} className="queue__item">
                    <h3>{gate.topic}</h3>
                    <p className="muted">Gate {gate.id}</p>
                    <pre>{gate.script_body}</pre>
                    <label>
                      Notes
                      <input
                        value={notes[gate.id] ?? ""}
                        onChange={(e) =>
                          setNotes((prev) => ({ ...prev, [gate.id]: e.target.value }))
                        }
                      />
                    </label>
                    <div className="queue__actions">
                      <button
                        type="button"
                        disabled={busy}
                        onClick={() => void decide(gate.id, true)}
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        className="danger"
                        disabled={busy}
                        onClick={() => void decide(gate.id, false)}
                      >
                        Reject
                      </button>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      )}

      {error ? <p className="error" role="alert">{error}</p> : null}
    </div>
  );
}
