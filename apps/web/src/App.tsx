import { useEffect, useState } from "react";
import { BusinessManagerMark } from "./BusinessManagerMark";
import FounderStudioPreview from "./FounderStudioPreview";

const PREVIEW_SESSION_KEY = "content-orchestrator.founder-studio.active";

function loadPreviewSession(): boolean {
  try {
    return sessionStorage.getItem(PREVIEW_SESSION_KEY) === "true";
  } catch {
    return false;
  }
}

export default function App() {
  const [active, setActive] = useState(() => loadPreviewSession());
  const [launchState, setLaunchState] = useState<"hidden" | "visible" | "exiting">(
    () => (loadPreviewSession() ? "visible" : "hidden"),
  );

  useEffect(() => {
    if (!active || launchState !== "visible") return;
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
  }, [active, launchState]);

  function continueToFounderStudio() {
    sessionStorage.setItem(PREVIEW_SESSION_KEY, "true");
    setLaunchState("visible");
    setActive(true);
  }

  function exitFounderStudio() {
    sessionStorage.removeItem(PREVIEW_SESSION_KEY);
    setLaunchState("hidden");
    setActive(false);
  }

  if (active) {
    return (
      <>
        <FounderStudioPreview onExit={exitFounderStudio} />
        {launchState !== "hidden" ? (
          <div
            aria-label="The Business Manager launch"
            className={launchState === "exiting" ? "business-launch business-launch--exiting" : "business-launch"}
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
        <div className="auth-lockup" aria-label="The Business Manager — Business Operating System">
          <BusinessManagerMark className="auth-lockup__mark" />
          <strong className="auth-lockup__name">The Business Manager</strong>
          <small className="auth-lockup__subtitle">Founder Studio Preview</small>
        </div>
        <div className="auth-form auth-form--approved">
          <h1 id="auth-title">Founder Studio</h1>
          <p className="auth-notice">
            Preview access only. This test uses browser-local data and cannot publish externally.
          </p>
          <button className="button button--primary auth-submit" type="button" onClick={continueToFounderStudio}>
            CONTINUE
          </button>
        </div>
      </section>
    </main>
  );
}
