import { useEffect, useState } from "react";
import LumoraDashboard from "./LumoraDashboard";
import { BusinessManagerMark } from "./BusinessManagerMark";

type Session = {
  token: string;
  workspaceId: string;
  email: string;
};

const STORAGE_KEY = "lumora.missionControl.session";
const PREVIEW_TOKEN = "founder-studio-preview-ui-only";
const PREVIEW_WORKSPACE_ID = "founder-studio-preview";

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
  const [launchState, setLaunchState] = useState<"hidden" | "visible" | "exiting">(
    () => (loadSession() ? "visible" : "hidden"),
  );

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

  function continueToFounderStudio() {
    const next: Session = {
      token: PREVIEW_TOKEN,
      workspaceId: PREVIEW_WORKSPACE_ID,
      email: "Founder Preview",
    };
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setLaunchState("visible");
    setSession(next);
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
          }}
        />
        {launchState !== "hidden" ? (
          <div
            aria-label="The Business Manager launch"
            className={
              launchState === "exiting"
                ? "business-launch business-launch--exiting"
                : "business-launch"
            }
            role="status"
          >
            <BusinessManagerMark className="business-launch__mark" />
            <p>The Business Manager</p>
            <span>We get it sorted.</span>
          </div>
        ) : null}
      </>
    );
  }

  return (
    <main className="auth-shell auth-shell--approved">
      <section className="auth-card" aria-labelledby="auth-title">
        <div
          className="auth-lockup"
          aria-label="The Business Manager — Business Operating System"
        >
          <BusinessManagerMark className="auth-lockup__mark" />
          <strong className="auth-lockup__name">The Business Manager</strong>
          <small className="auth-lockup__subtitle">Founder Studio Preview</small>
        </div>
        <div className="auth-form auth-form--approved">
          <h1 id="auth-title">Founder Studio</h1>
          <p className="auth-notice">
            Preview access only. Sign-in will be restored before customer access is enabled.
          </p>
          <button
            className="button button--primary auth-submit"
            type="button"
            onClick={continueToFounderStudio}
          >
            CONTINUE
          </button>
        </div>
      </section>
    </main>
  );
}
