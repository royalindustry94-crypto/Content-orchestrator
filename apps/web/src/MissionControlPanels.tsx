import { useState, type FormEvent, type ReactNode } from "react";
import {
  createContentJob,
  createWorkspace,
  postMissionAction,
  type ActivityFeed,
  type ContentCommand,
  type CostControl,
  type ExecutiveInsights,
  type QuickActionResult,
  type SystemHealth,
  type WorkerTimeline,
} from "./api";

function formatDate(value: string | null | undefined): string {
  if (!value) return "Unavailable";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function money(value: string | null | undefined): string {
  if (value == null) return "Unavailable";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 4,
  }).format(Number(value));
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

function Empty({ children }: { children: string }) {
  return <div className="empty">{children}</div>;
}

function StatusPill({ value }: { value: string }) {
  const normalized = value.toLowerCase();
  const tone =
    ["online", "healthy", "active", "success", "passing", "green", "completed", "published"].includes(
      normalized,
    )
      ? "good"
      : ["failed", "offline", "dead", "expired", "red", "failure"].includes(normalized)
        ? "bad"
        : "warn";
  return <span className={`status status--${tone}`}>{value.replaceAll("_", " ")}</span>;
}

export function ActivityFeedView({ data }: { data: ActivityFeed }) {
  if (data.items.length === 0) return <Empty>No activity recorded yet.</Empty>;
  return (
    <div className="alert-list">
      {data.items.map((item) => (
        <article className={`alert-card alert-card--${item.severity}`} key={item.id}>
          <div>
            <h3>{item.title}</h3>
            <p>{item.detail ?? item.kind}</p>
            <p className="freshness" style={{ textAlign: "left" }}>
              {formatDate(item.occurred_at)} · {item.source}
            </p>
          </div>
          <StatusPill value={item.severity} />
        </article>
      ))}
    </div>
  );
}

export function SystemHealthView({ data }: { data: SystemHealth }) {
  if (data.indicators.length === 0) {
    return <Empty>No health indicators are available.</Empty>;
  }
  return (
    <div className="metrics-grid">
      {data.indicators.map((indicator) => (
        <article className={`metric health health--${indicator.status}`} key={indicator.key}>
          <p>{indicator.label}</p>
          <strong><StatusPill value={indicator.status} /></strong>
          <span>{indicator.detail}</span>
        </article>
      ))}
    </div>
  );
}

export function CostControlView({ data }: { data: CostControl }) {
  return (
    <>
      <div className="metrics-grid metrics-grid--compact">
        <MetricCard label="Daily AI Spend" value={money(data.daily_ai_spend_usd)} />
        <MetricCard label="Monthly AI Spend" value={money(data.monthly_ai_spend_usd)} />
        <MetricCard label="Budget Remaining (Daily)" value={money(data.budget_remaining_daily_usd)} />
        <MetricCard label="Budget Remaining (Monthly)" value={money(data.budget_remaining_monthly_usd)} />
        <MetricCard label="Projected Month End" value={money(data.projected_month_end_usd)} />
      </div>
      <h3 className="ops-section-title">Spend by provider</h3>
      {data.by_provider.length === 0 ? (
        <Empty>No provider spend this period.</Empty>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Provider</th>
                <th>Today</th>
                <th>Month</th>
              </tr>
            </thead>
            <tbody>
              {data.by_provider.map((row) => (
                <tr key={row.provider}>
                  <td><strong>{row.provider}</strong></td>
                  <td>{money(row.today_usd)}</td>
                  <td>{money(row.month_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <h3 className="ops-section-title">Top 10 most expensive jobs</h3>
      {data.top_expensive_jobs.length === 0 ? (
        <Empty>No costly jobs recorded.</Empty>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Topic</th>
                <th>Stage</th>
                <th>Provider</th>
                <th>Cost</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {data.top_expensive_jobs.map((job, index) => (
                <tr key={`${job.content_item_id ?? "x"}-${index}`}>
                  <td>{job.topic ?? "—"}</td>
                  <td>{job.stage ?? "—"}</td>
                  <td>{job.provider ?? "—"}</td>
                  <td>{money(job.cost_usd)}</td>
                  <td>{formatDate(job.completed_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

export function WorkerTimelineView({ data }: { data: WorkerTimeline }) {
  if (data.workers.length === 0) return <Empty>No workers registered.</Empty>;
  return (
    <div className="timeline-stack">
      {data.workers.map((worker) => (
        <section className="timeline-card" key={worker.worker_id}>
          <header>
            <div>
              <h3>{worker.name}</h3>
              <p>
                <StatusPill value={worker.status} /> · Heartbeat {formatDate(worker.last_heartbeat_at)}
              </p>
            </div>
            <div className="timeline-stats">
              <span>Avg {worker.average_execution_seconds == null ? "Unavailable" : `${worker.average_execution_seconds}s`}</span>
              <span>Fail {worker.failure_percent}%</span>
              <span>Retry {worker.retry_percent}%</span>
            </div>
          </header>
          <p className="mono">Current task: {worker.current_task ?? "—"}</p>
          {worker.jobs.length === 0 ? (
            <Empty>No recent jobs for this worker.</Empty>
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Stage</th>
                    <th>Status</th>
                    <th>Attempt</th>
                    <th>Duration</th>
                    <th>Completed</th>
                  </tr>
                </thead>
                <tbody>
                  {worker.jobs.map((job) => (
                    <tr key={job.assignment_id}>
                      <td>{job.stage}</td>
                      <td><StatusPill value={job.status} /></td>
                      <td>{job.attempt_number}</td>
                      <td>{job.duration_seconds == null ? "—" : `${job.duration_seconds}s`}</td>
                      <td>{formatDate(job.completed_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      ))}
    </div>
  );
}

export function ContentCommandView({ data }: { data: ContentCommand }) {
  const hasActivity = [
    data.ideas,
    data.scripts,
    data.voiceovers,
    data.videos_rendering,
    data.ready_for_review,
    data.waiting_for_approval,
    data.publishing,
    data.published,
    data.failed,
  ].some((value) => value > 0);
  return (
    <>
      <div className="metrics-grid">
        <MetricCard label="Ideas" value={data.ideas} />
        <MetricCard label="Scripts" value={data.scripts} />
        <MetricCard label="Voiceovers" value={data.voiceovers} />
        <MetricCard label="Videos Rendering" value={data.videos_rendering} />
        <MetricCard label="Ready For Review" value={data.ready_for_review} />
        <MetricCard label="Waiting For Approval" value={data.waiting_for_approval} />
        <MetricCard label="Publishing" value={data.publishing} />
        <MetricCard label="Published" value={data.published} />
        <MetricCard label="Failed" value={data.failed} />
      </div>
      {!hasActivity ? <Empty>No content activity has been recorded yet.</Empty> : null}
    </>
  );
}

export function InsightsView({ data }: { data: ExecutiveInsights }) {
  return (
    <>
      <div className="metrics-grid metrics-grid--compact">
        <MetricCard
          label="Biggest Cost Today"
          value={money(data.biggest_cost_today_usd)}
          detail={data.biggest_cost_today_label ?? undefined}
        />
        <MetricCard label="Most Active Worker" value={data.most_active_worker ?? "Unavailable"} />
        <MetricCard label="Most Active Customer" value={data.most_active_customer ?? "Unavailable"} />
        <MetricCard label="Highest Risk" value={data.highest_risk} />
      </div>
      <div className="insight-grid">
        <section>
          <h3>Today&apos;s achievements</h3>
          {data.todays_achievements.length ? (
            <ul>{data.todays_achievements.map((item) => <li key={item}>{item}</li>)}</ul>
          ) : <Empty>No achievements recorded today.</Empty>}
        </section>
        <section>
          <h3>Today&apos;s failures</h3>
          {data.todays_failures.length ? (
            <ul>{data.todays_failures.map((item) => <li key={item}>{item}</li>)}</ul>
          ) : <Empty>No failures recorded today.</Empty>}
        </section>
        <section>
          <h3>Suggested next action</h3>
          <p>{data.suggested_next_action}</p>
        </section>
      </div>
    </>
  );
}

export function QuickActionsView({
  token,
  workspaceId,
  onWorkspaceCreated,
}: {
  token: string;
  workspaceId: string;
  onWorkspaceCreated?: (id: string) => void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [result, setResult] = useState<QuickActionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [workspaceName, setWorkspaceName] = useState("");
  const [pipelineTopic, setPipelineTopic] = useState("");

  const run = async (action: string, fn: () => Promise<QuickActionResult | { message: string }>) => {
    setBusy(action);
    setError(null);
    try {
      const next = await fn();
      if ("action" in next) {
        setResult(next);
      } else {
        setResult({
          action,
          ok: true,
          affected: 1,
          message: next.message,
          details: {},
        });
      }
    } catch (err) {
      setResult(null);
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setBusy(null);
    }
  };

  const createWs = async (event: FormEvent) => {
    event.preventDefault();
    await run("create_workspace", async () => {
      const ws = await createWorkspace(token, workspaceName);
      onWorkspaceCreated?.(ws.id);
      return { message: `Created workspace ${ws.name} (${ws.id})` };
    });
  };

  const createPipeline = async (event: FormEvent) => {
    event.preventDefault();
    await run("create_pipeline", async () => {
      const job = await createContentJob(token, workspaceId, {
        topic: pipelineTopic,
      });
      return {
        message: `Created pipeline ${job.pipeline_run_id} for ${job.topic}`,
      };
    });
  };

  return (
    <>
      <div className="actions-grid">
        {[
          ["pause-workers", "Pause Workers"],
          ["resume-workers", "Resume Workers"],
          ["emergency-stop", "Emergency Stop"],
          ["retry-failed-jobs", "Retry Failed Jobs"],
          ["clear-dead-letter", "Clear Dead Letter Queue"],
          ["sync-github", "Sync GitHub"],
        ].map(([action, label]) => (
          <button
            key={action}
            type="button"
            className={action === "emergency-stop" ? "action-btn action-btn--danger" : "action-btn"}
            disabled={busy !== null}
            onClick={() =>
              void run(action, () =>
                postMissionAction(
                  token,
                  workspaceId,
                  action as
                    | "pause-workers"
                    | "resume-workers"
                    | "emergency-stop"
                    | "retry-failed-jobs"
                    | "clear-dead-letter"
                    | "sync-github",
                ),
              )
            }
          >
            {busy === action ? "Working…" : label}
          </button>
        ))}
      </div>

      <form className="ops-form" onSubmit={(e) => void createWs(e)}>
        <h3>Create Workspace</h3>
        <div className="ops-form__grid">
          <input
            aria-label="Workspace name"
            required
            value={workspaceName}
            onChange={(e) => setWorkspaceName(e.target.value)}
            placeholder="Workspace name"
          />
        </div>
        <button type="submit" disabled={busy !== null}>
          {busy === "create_workspace" ? "Creating…" : "Create Workspace"}
        </button>
      </form>

      <form className="ops-form" onSubmit={(e) => void createPipeline(e)}>
        <h3>Create Pipeline</h3>
        <div className="ops-form__grid">
          <input
            aria-label="Pipeline topic"
            required
            value={pipelineTopic}
            onChange={(e) => setPipelineTopic(e.target.value)}
            placeholder="Pipeline topic"
          />
        </div>
        <button type="submit" disabled={busy !== null}>
          {busy === "create_pipeline" ? "Creating…" : "Create Pipeline"}
        </button>
      </form>

      {error ? <p className="ops-form__error">{error}</p> : null}
      {result ? (
        <div className={`alert-card alert-card--${result.ok ? "info" : "critical"}`}>
          <div>
            <h3>{result.action}</h3>
            <p>{result.message}</p>
          </div>
          <strong>{result.affected}</strong>
        </div>
      ) : null}
    </>
  );
}
