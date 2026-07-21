import { useEffect, useState } from "react";

type ReadinessStatus = "checking" | "ok" | "unavailable";

/**
 * Milestone-1 scope: confirm the frontend can reach the API's readiness
 * endpoint. The dashboard (pipeline status, alerts, spend, etc. per the
 * v2 spec) belongs to a later milestone that has the data model and auth
 * to back it; this component intentionally covers only the health check.
 */
export default function App() {
  const [status, setStatus] = useState<ReadinessStatus>("checking");

  useEffect(() => {
    let cancelled = false;

    async function checkReadiness() {
      try {
        const response = await fetch("/api/health/ready");
        if (!cancelled) {
          setStatus(response.ok ? "ok" : "unavailable");
        }
      } catch {
        if (!cancelled) {
          setStatus("unavailable");
        }
      }
    }

    checkReadiness();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem" }}>
      <h1>Content Orchestrator</h1>
      <p>
        API status:{" "}
        <strong>
          {status === "checking" && "checking..."}
          {status === "ok" && "connected"}
          {status === "unavailable" && "unavailable"}
        </strong>
      </p>
    </main>
  );
}
