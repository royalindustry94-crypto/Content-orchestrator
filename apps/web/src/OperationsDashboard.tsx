import { useCallback, useEffect, useState, type ReactNode } from "react";
import {
  getExecutiveDashboard,
  getOperationsAlerts,
  getPipelineMonitor,
  getWorkerMonitor,
  type Alerts,
  type ExecutiveDashboard,
  type PipelineMonitor,
  type WorkerMonitor,
} from "./api";

type Screen = "executive" | "workers" | "pipelines" | "alerts";

type Props = {
  token: string;
  workspaceId: string;
  email: string;
  onSignOut: () => void;
};

const NAV: Array<{ id: Screen; label: string }> = [
  { id: "executive", label: "Executive Dashboard" },
  { id: "workers", label: "Worker Monitor" },
  { id: "pipelines", label: "Pipeline Monitor" },
  { id: "alerts", label: "Alerts" },
];

function formatDate(value: string | null): string {
  if (!value) return "Unavailable";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function money(value: string): string {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(Number(value));
}

function StatusPill({ value }: { value: string }) {
  const normalized = value.toLowerCase();
  const tone =
    ["online", "healthy", "active", "success", "passing", "green"].includes(normalized)
      ? "good"
      : ["failed", "offline", "dead", "expired"].includes(normalized)
        ? "bad"
        : "warn";
  return <span className={`status status--${tone}`}>{value.replaceAll("_", " ")}</span>;
}

function Empty({ children }: { children: string }) {
  return <div className="empty">{children}</div>;
}

function Loading() {
  return (
    <div className="loading-grid" aria-label="Loading operations data" aria-busy="true">
      {Array.from({ length: 8 }, (_, index) => (
        <div className="skeleton" key={index} />
      ))}
    </div>
  );
}

function MetricCard({
  label,
  value,
  detail,
}: {
  label: string;
  value: ReactNode;
  detail?: string;
}) {
  return (
    <article className="metric">
      <p>{label}</p>
      <strong>{value}</strong>
      {detail ? <span>{detail}</span> : null}
    </article>
  );
}

function Executive({ data }: { data: ExecutiveDashboard }) {
  const deployment = data.deployment;
  return (
    <>
      <div className="metrics-grid">
        <MetricCard label="Workers Online" value={data.workers_online} />
        <MetricCard label="Workers Busy" value={data.workers_busy} />
        <MetricCard label="Jobs Running" value={data.jobs_running} />
        <MetricCard label="Jobs Queued" value={data.jobs_queued} />
        <MetricCard label="Jobs Failed" value={data.jobs_failed} />
        <MetricCard label="Human Reviews Waiting" value={data.human_reviews_waiting} />
        <MetricCard label="Spend Today" value={money(data.spend_today_usd)} />
        <MetricCard label="Spend This Month" value={money(data.spend_month_usd)} />
        <MetricCard label="Active Workspaces" value={data.active_workspaces} />
        <MetricCard
          label="CI Status"
          value={<StatusPill value={deployment.ci_status} />}
        />
        <MetricCard
          label="Current Git Branch"
          value={deployment.git_branch ?? "Unavailable"}
          detail={deployment.commit_sha?.slice(0, 8)}
        />
        <MetricCard
          label="Last Deployment"
          value={formatDate(deployment.deployed_at)}
          detail={deployment.ci_url ? "CI details available" : undefined}
        />
      </div>
      <p className="freshness">Updated {formatDate(data.generated_at)}</p>
    </>
  );
}

function Workers({ data }: { data: WorkerMonitor }) {
  if (data.workers.length === 0) return <Empty>No workers are registered.</Empty>;
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            <th>Worker Name</th>
            <th>Status</th>
            <th>Current Job</th>
            <th>Queue</th>
            <th>Last Heartbeat</th>
            <th>Retries</th>
            <th>Completed</th>
            <th>Failed</th>
            <th>Lease</th>
          </tr>
        </thead>
        <tbody>
          {data.workers.map((worker) => (
            <tr key={worker.id}>
              <td><strong>{worker.name}</strong></td>
              <td><StatusPill value={worker.status} /></td>
              <td className="mono">{worker.current_job ?? "—"}</td>
              <td>{worker.queue}</td>
              <td>{formatDate(worker.last_heartbeat_at)}</td>
              <td>{worker.retry_count}</td>
              <td>{worker.jobs_completed}</td>
              <td>{worker.jobs_failed}</td>
              <td><StatusPill value={worker.lease_status} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Pipelines({ data }: { data: PipelineMonitor }) {
  return (
    <>
      <div className="metrics-grid metrics-grid--compact">
        <MetricCard label="Active Pipelines" value={data.active_pipelines} />
        <MetricCard label="Queue Depth" value={data.queue_depth} />
        <MetricCard label="Failed Pipelines" value={data.failed_pipelines} />
        <MetricCard label="Retrying Pipelines" value={data.retrying_pipelines} />
        <MetricCard label="Dead Letter Queue" value={data.dead_letter_queue} />
        <MetricCard label="Review Gates" value={data.review_gates} />
        <MetricCard label="Publish Queue" value={data.publish_queue} />
      </div>
      {data.pipelines.length === 0 ? (
        <Empty>No active or failed pipelines.</Empty>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Pipeline</th>
                <th>Status</th>
                <th>Current Stage</th>
                <th>Hold Reason</th>
                <th>Last Update</th>
              </tr>
            </thead>
            <tbody>
              {data.pipelines.map((pipeline) => (
                <tr key={pipeline.id}>
                  <td className="mono">{pipeline.id}</td>
                  <td><StatusPill value={pipeline.status} /></td>
                  <td>{pipeline.current_stage}</td>
                  <td>{pipeline.pause_reason ?? "—"}</td>
                  <td>{formatDate(pipeline.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function AlertList({ data }: { data: Alerts }) {
  if (data.alerts.length === 0) {
    return <Empty>No active operational alerts.</Empty>;
  }
  return (
    <div className="alert-list">
      {data.alerts.map((alert) => (
        <article className={`alert-card alert-card--${alert.severity}`} key={alert.key}>
          <div>
            <h3>{alert.title}</h3>
            <p>{alert.message}</p>
          </div>
          <strong>{alert.count}</strong>
        </article>
      ))}
    </div>
  );
}

export default function OperationsDashboard({
  token,
  workspaceId,
  email,
  onSignOut,
}: Props) {
  const [screen, setScreen] = useState<Screen>("executive");
  const [data, setData] = useState<
    ExecutiveDashboard | WorkerMonitor | PipelineMonitor | Alerts | null
  >(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const next =
        screen === "executive"
          ? await getExecutiveDashboard(token, workspaceId)
          : screen === "workers"
            ? await getWorkerMonitor(token, workspaceId)
            : screen === "pipelines"
              ? await getPipelineMonitor(token, workspaceId)
              : await getOperationsAlerts(token, workspaceId);
      setData(next);
    } catch (err) {
      setData(null);
      setError(err instanceof Error ? err.message : "Operations data failed to load");
    } finally {
      setLoading(false);
    }
  }, [screen, token, workspaceId]);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="ops-shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">Lumora</p>
          <h1>Operations</h1>
          <p className="workspace-id">Workspace {workspaceId.slice(0, 8)}</p>
        </div>
        <nav aria-label="Operations screens">
          {NAV.map((item) => (
            <button
              className={screen === item.id ? "nav-item nav-item--active" : "nav-item"}
              key={item.id}
              onClick={() => setScreen(item.id)}
              type="button"
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar__account">
          <span>{email}</span>
          <button type="button" onClick={onSignOut}>Sign out</button>
        </div>
      </aside>

      <main className="ops-main">
        <header className="page-header">
          <div>
            <p className="eyebrow">Control plane</p>
            <h2>{NAV.find((item) => item.id === screen)?.label}</h2>
          </div>
          <button className="refresh" type="button" onClick={() => void load()} disabled={loading}>
            {loading ? "Refreshing…" : "Refresh"}
          </button>
        </header>

        {error ? (
          <section className="error-state" role="alert">
            <h3>Operations data unavailable</h3>
            <p>{error}</p>
            <button type="button" onClick={() => void load()}>Retry</button>
          </section>
        ) : loading ? (
          <Loading />
        ) : screen === "executive" && data ? (
          <Executive data={data as ExecutiveDashboard} />
        ) : screen === "workers" && data ? (
          <Workers data={data as WorkerMonitor} />
        ) : screen === "pipelines" && data ? (
          <Pipelines data={data as PipelineMonitor} />
        ) : data ? (
          <AlertList data={data as Alerts} />
        ) : null}
      </main>
    </div>
  );
}
