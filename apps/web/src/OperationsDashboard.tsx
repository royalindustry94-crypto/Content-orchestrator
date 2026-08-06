import {
  useCallback,
  useEffect,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  createLead,
  getActivityFeed,
  getContentCommand,
  getCostControl,
  getCustomers,
  getExecutiveDashboard,
  getExecutiveMode,
  getExecutiveInsights,
  getGitHubStatus,
  getLeads,
  getNotifications,
  getOperationsAlerts,
  getPipelineMonitor,
  getSpendDashboard,
  getSystemHealth,
  getUniversalTimeline,
  getLiveLogs,
  getWorkerMonitor,
  getWorkerTimeline,
  updateLead,
  type ActivityFeed,
  type Alerts,
  type ContentCommand,
  type CostControl,
  type Customers,
  type ExecutiveDashboard,
  type ExecutiveMode,
  type ExecutiveInsights,
  type GitHubOut,
  type Leads,
  type LiveLogs,
  type Notifications,
  type PipelineMonitor,
  type SpendDashboard,
  type SystemHealth,
  type WorkerMonitor,
  type WorkerTimeline,
} from "./api";
import {
  ActivityFeedView,
  ContentCommandView,
  CostControlView,
  InsightsView,
  QuickActionsView,
  SystemHealthView,
  WorkerTimelineView,
} from "./MissionControlPanels";
import {
  AssistantPanel,
  CommandPalette,
  ExecutiveModeView,
  GlobalSearchBar,
  LiveLogsView,
  UniversalTimelineView,
} from "./MissionControlV4";

type Screen =
  | "executive-mode"
  | "timeline"
  | "logs"
  | "assistant"
  | "executive"
  | "activity"
  | "health"
  | "cost"
  | "worker-timeline"
  | "content"
  | "actions"
  | "insights"
  | "workers"
  | "leads"
  | "customers"
  | "spend"
  | "github"
  | "pipelines"
  | "notifications"
  | "alerts";

type Props = {
  token: string;
  workspaceId: string;
  email: string;
  onSignOut: () => void;
};

const NAV: Array<{ id: Screen; label: string }> = [
  { id: "executive-mode", label: "Executive Mode" },
  { id: "timeline", label: "Universal Timeline" },
  { id: "logs", label: "Live Logs" },
  { id: "assistant", label: "AI Assistant" },
  { id: "executive", label: "Executive Dashboard" },
  { id: "activity", label: "Live Activity" },
  { id: "health", label: "System Health" },
  { id: "cost", label: "Cost Control" },
  { id: "worker-timeline", label: "Worker Timeline" },
  { id: "content", label: "Content Command" },
  { id: "actions", label: "Quick Actions" },
  { id: "insights", label: "Executive Insights" },
  { id: "workers", label: "AI Workers" },
  { id: "leads", label: "Leads CRM" },
  { id: "customers", label: "Customers" },
  { id: "spend", label: "Spend" },
  { id: "github", label: "GitHub" },
  { id: "pipelines", label: "AI Pipeline" },
  { id: "notifications", label: "Notifications" },
  { id: "alerts", label: "Alerts" },
];

const LEAD_STATUSES = [
  "new",
  "contacted",
  "qualified",
  "negotiation",
  "won",
  "lost",
  "nurturing",
];

function formatDate(value: string | null | undefined): string {
  if (!value) return "Unavailable";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function formatDay(value: string | null | undefined): string {
  if (!value) return "—";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium" }).format(
    new Date(`${value}T00:00:00Z`),
  );
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

function resource(value: number | null | undefined): string {
  if (value == null) return "Unavailable";
  return `${value.toFixed(0)}%`;
}

function StatusPill({ value }: { value: string }) {
  const normalized = value.toLowerCase();
  const tone =
    ["online", "healthy", "active", "success", "passing", "green", "won", "pro"].includes(
      normalized,
    )
      ? "good"
      : ["failed", "offline", "dead", "expired", "lost", "failure", "cancelled"].includes(
            normalized,
          )
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
            <th>Live Status</th>
            <th>Current Task</th>
            <th>Queue</th>
            <th>CPU</th>
            <th>Memory</th>
            <th>Last Heartbeat</th>
            <th>Retries</th>
            <th>Completed Today</th>
            <th>Failed Today</th>
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
              <td className="mono">{worker.current_task ?? worker.current_job ?? "—"}</td>
              <td>{worker.queue}</td>
              <td>{resource(worker.cpu_percent)}</td>
              <td>{resource(worker.memory_percent)}</td>
              <td>{formatDate(worker.last_heartbeat_at)}</td>
              <td>{worker.retry_count}</td>
              <td>{worker.jobs_completed_today}</td>
              <td>{worker.jobs_failed_today}</td>
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
        <MetricCard label="Jobs Completed" value={data.jobs_completed} />
        <MetricCard label="Jobs Waiting" value={data.jobs_waiting} />
        <MetricCard label="Jobs Failed" value={data.jobs_failed} />
        <MetricCard label="Human Reviews Waiting" value={data.human_reviews_waiting} />
        <MetricCard label="Publishing Queue" value={data.publishing_queue} />
        <MetricCard label="Active Pipelines" value={data.active_pipelines} />
        <MetricCard label="Failed Pipelines" value={data.failed_pipelines} />
        <MetricCard label="Dead Letter Queue" value={data.dead_letter_queue} />
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

function AlertList({
  items,
  empty,
}: {
  items: Alerts["alerts"] | Notifications["notifications"];
  empty: string;
}) {
  if (items.length === 0) return <Empty>{empty}</Empty>;
  return (
    <div className="alert-list">
      {items.map((alert) => (
        <article className={`alert-card alert-card--${alert.severity}`} key={alert.key}>
          <div>
            <h3>{alert.title}</h3>
            <p>{alert.message}</p>
            {alert.occurred_at ? (
              <p className="freshness" style={{ textAlign: "left" }}>
                {formatDate(alert.occurred_at)}
              </p>
            ) : null}
          </div>
          <strong>{alert.count}</strong>
        </article>
      ))}
    </div>
  );
}

function CustomersView({ data }: { data: Customers }) {
  return (
    <>
      <div className="metrics-grid metrics-grid--compact">
        <MetricCard label="Beta Users" value={data.beta_users} />
        <MetricCard label="Active Users" value={data.active_users} />
        <MetricCard label="Paying Users" value={data.paying_users} />
        <MetricCard label="Trial Users" value={data.trial_users} />
        <MetricCard
          label="Revenue MTD"
          value={money(data.revenue_mtd_usd)}
          detail={data.revenue_source}
        />
      </div>
      {data.customers.length === 0 ? (
        <Empty>No customer workspaces under your admin memberships.</Empty>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Workspace</th>
                <th>Plan</th>
                <th>Subscription</th>
                <th>Members</th>
                <th>Stripe Customer</th>
                <th>Period End</th>
              </tr>
            </thead>
            <tbody>
              {data.customers.map((customer) => (
                <tr key={customer.workspace_id}>
                  <td><strong>{customer.name}</strong></td>
                  <td>{customer.plan}</td>
                  <td><StatusPill value={customer.subscription_status} /></td>
                  <td>{customer.member_count}</td>
                  <td className="mono">{customer.stripe_customer_id ?? "—"}</td>
                  <td>{formatDate(customer.current_period_end)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function SpendView({ data }: { data: SpendDashboard }) {
  return (
    <>
      <div className="metrics-grid metrics-grid--compact">
        <MetricCard label="Today" value={money(data.today_usd)} />
        <MetricCard label="This Week" value={money(data.week_usd)} />
        <MetricCard label="This Month" value={money(data.month_usd)} />
        <MetricCard
          label="Budget Remaining (Daily)"
          value={money(data.budget_remaining_daily_usd)}
          detail={data.daily_cap_usd ? `Cap ${money(data.daily_cap_usd)}` : "No daily cap"}
        />
        <MetricCard
          label="Budget Remaining (Monthly)"
          value={money(data.budget_remaining_monthly_usd)}
          detail={data.monthly_cap_usd ? `Cap ${money(data.monthly_cap_usd)}` : "No monthly cap"}
        />
      </div>
      {data.by_provider.length === 0 ? (
        <Empty>No committed spend for this workspace yet.</Empty>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Provider</th>
                <th>Today</th>
                <th>This Week</th>
                <th>This Month</th>
              </tr>
            </thead>
            <tbody>
              {data.by_provider.map((row) => (
                <tr key={row.provider}>
                  <td><strong>{row.provider}</strong></td>
                  <td>{money(row.today_usd)}</td>
                  <td>{money(row.week_usd)}</td>
                  <td>{money(row.month_usd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function GitHubView({ data }: { data: GitHubOut }) {
  return (
    <>
      <div className="metrics-grid metrics-grid--compact">
        <MetricCard
          label="Repository"
          value={data.repository ?? "Unavailable"}
          detail={data.available ? "Live GitHub API" : data.unavailable_reason ?? "Unavailable"}
        />
        <MetricCard
          label="Branch"
          value={data.branch_status.name ?? "Unavailable"}
          detail={data.branch_status.sha?.slice(0, 8)}
        />
        <MetricCard
          label="Branch CI"
          value={<StatusPill value={data.branch_status.ci_status} />}
        />
        <MetricCard label="Open PRs" value={data.open_pull_requests.length} />
        <MetricCard label="Failed Actions" value={data.failed_actions.length} />
      </div>

      {!data.available ? (
        <Empty>{data.unavailable_reason ?? "GitHub status unavailable."}</Empty>
      ) : null}

      <h3 className="ops-section-title">Latest commits</h3>
      {data.latest_commits.length === 0 ? (
        <Empty>No commits returned.</Empty>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>SHA</th>
                <th>Message</th>
                <th>Author</th>
                <th>When</th>
              </tr>
            </thead>
            <tbody>
              {data.latest_commits.map((commit) => (
                <tr key={commit.sha}>
                  <td className="mono">
                    {commit.url ? (
                      <a href={commit.url} target="_blank" rel="noreferrer">
                        {commit.sha.slice(0, 8)}
                      </a>
                    ) : (
                      commit.sha.slice(0, 8)
                    )}
                  </td>
                  <td>{commit.message}</td>
                  <td>{commit.author ?? "—"}</td>
                  <td>{formatDate(commit.committed_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h3 className="ops-section-title">Open pull requests</h3>
      {data.open_pull_requests.length === 0 ? (
        <Empty>No open pull requests.</Empty>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>PR</th>
                <th>Title</th>
                <th>Author</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {data.open_pull_requests.map((pr) => (
                <tr key={pr.number}>
                  <td className="mono">
                    {pr.url ? (
                      <a href={pr.url} target="_blank" rel="noreferrer">#{pr.number}</a>
                    ) : (
                      `#${pr.number}`
                    )}
                  </td>
                  <td>{pr.title}</td>
                  <td>{pr.author ?? "—"}</td>
                  <td>{formatDate(pr.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h3 className="ops-section-title">Failed Actions</h3>
      {data.failed_actions.length === 0 ? (
        <Empty>No recent failed Actions runs.</Empty>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Workflow</th>
                <th>Conclusion</th>
                <th>Branch</th>
                <th>Updated</th>
              </tr>
            </thead>
            <tbody>
              {data.failed_actions.map((run) => (
                <tr key={run.id}>
                  <td>
                    {run.url ? (
                      <a href={run.url} target="_blank" rel="noreferrer">{run.name}</a>
                    ) : (
                      run.name
                    )}
                  </td>
                  <td><StatusPill value={run.conclusion ?? run.status} /></td>
                  <td>{run.branch ?? "—"}</td>
                  <td>{formatDate(run.updated_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

type ScreenData =
  | ExecutiveDashboard
  | WorkerMonitor
  | PipelineMonitor
  | Alerts
  | Notifications
  | Leads
  | Customers
  | SpendDashboard
  | GitHubOut
  | ActivityFeed
  | SystemHealth
  | CostControl
  | WorkerTimeline
  | ContentCommand
  | ExecutiveInsights
  | ExecutiveMode
  | LiveLogs
  | { kind: "actions" };

export default function OperationsDashboard({
  token,
  workspaceId,
  email,
  onSignOut,
}: Props) {
  const [screen, setScreen] = useState<Screen>("executive-mode");
  const [data, setData] = useState<ScreenData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [leadFilters, setLeadFilters] = useState({
    search: "",
    status: "",
    source: "",
  });

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let next: ScreenData;
      switch (screen) {
        case "executive-mode":
          next = await getExecutiveMode(token, workspaceId);
          break;
        case "timeline":
          next = await getUniversalTimeline(token, workspaceId);
          break;
        case "logs":
          next = await getLiveLogs(token, workspaceId);
          break;
        case "assistant":
          next = { kind: "actions" };
          break;
        case "executive":
          next = await getExecutiveDashboard(token, workspaceId);
          break;
        case "workers":
          next = await getWorkerMonitor(token, workspaceId);
          break;
        case "pipelines":
          next = await getPipelineMonitor(token, workspaceId);
          break;
        case "alerts":
          next = await getOperationsAlerts(token, workspaceId);
          break;
        case "notifications":
          next = await getNotifications(token, workspaceId);
          break;
        case "leads":
          next = await getLeads(token, workspaceId, leadFilters);
          break;
        case "customers":
          next = await getCustomers(token, workspaceId);
          break;
        case "spend":
          next = await getSpendDashboard(token, workspaceId);
          break;
        case "github":
          next = await getGitHubStatus(token, workspaceId);
          break;
        case "activity":
          next = await getActivityFeed(token, workspaceId);
          break;
        case "health":
          next = await getSystemHealth(token, workspaceId);
          break;
        case "cost":
          next = await getCostControl(token, workspaceId);
          break;
        case "worker-timeline":
          next = await getWorkerTimeline(token, workspaceId);
          break;
        case "content":
          next = await getContentCommand(token, workspaceId);
          break;
        case "insights":
          next = await getExecutiveInsights(token, workspaceId);
          break;
        case "actions":
          next = { kind: "actions" };
          break;
      }
      setData(next);
    } catch (err) {
      setData(null);
      setError(err instanceof Error ? err.message : "Operations data failed to load");
    } finally {
      setLoading(false);
    }
  }, [screen, token, workspaceId, leadFilters]);

  useEffect(() => {
    void load();
  }, [load]);

  useEffect(() => {
    if (
      screen !== "notifications"
      && screen !== "activity"
      && screen !== "timeline"
      && screen !== "logs"
    ) return;
    const timer = window.setInterval(() => {
      void load();
    }, 15000);
    return () => window.clearInterval(timer);
  }, [screen, load]);

  return (
    <div className="ops-shell">
      <CommandPalette
        token={token}
        workspaceId={workspaceId}
        navigate={(next) => setScreen(next as Screen)}
      />
      <aside className="sidebar">
        <div>
          <p className="eyebrow">Lumora</p>
          <h1>Mission Control</h1>
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
        <GlobalSearchBar
          token={token}
          workspaceId={workspaceId}
          onOpen={(type) => {
            const targets: Record<string, Screen> = {
              customer: "customers",
              lead: "leads",
              pipeline: "pipelines",
              worker: "worker-timeline",
              job: "pipelines",
              content: "content",
              review: "content",
              video: "content",
              log: "logs",
              github: "github",
            };
            setScreen(targets[type] ?? "timeline");
          }}
        />
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
        ) : screen === "executive-mode" && data ? (
          <ExecutiveModeView data={data as ExecutiveMode} />
        ) : screen === "timeline" && data ? (
          <UniversalTimelineView data={data as ActivityFeed} />
        ) : screen === "logs" && data ? (
          <LiveLogsView
            token={token}
            workspaceId={workspaceId}
            initial={data as LiveLogs}
          />
        ) : screen === "assistant" ? (
          <AssistantPanel token={token} workspaceId={workspaceId} />
        ) : screen === "executive" && data ? (
          <Executive data={data as ExecutiveDashboard} />
        ) : screen === "workers" && data ? (
          <Workers data={data as WorkerMonitor} />
        ) : screen === "pipelines" && data ? (
          <Pipelines data={data as PipelineMonitor} />
        ) : screen === "alerts" && data ? (
          <AlertList
            items={(data as Alerts).alerts}
            empty="No active operational alerts."
          />
        ) : screen === "notifications" && data ? (
          <AlertList
            items={(data as Notifications).notifications}
            empty="No active notifications."
          />
        ) : screen === "customers" && data ? (
          <CustomersView data={data as Customers} />
        ) : screen === "spend" && data ? (
          <SpendView data={data as SpendDashboard} />
        ) : screen === "github" && data ? (
          <GitHubView data={data as GitHubOut} />
        ) : screen === "activity" && data ? (
          <ActivityFeedView data={data as ActivityFeed} />
        ) : screen === "health" && data ? (
          <SystemHealthView data={data as SystemHealth} />
        ) : screen === "cost" && data ? (
          <CostControlView data={data as CostControl} />
        ) : screen === "worker-timeline" && data ? (
          <WorkerTimelineView data={data as WorkerTimeline} />
        ) : screen === "content" && data ? (
          <ContentCommandView data={data as ContentCommand} />
        ) : screen === "insights" && data ? (
          <InsightsView data={data as ExecutiveInsights} />
        ) : screen === "actions" ? (
          <QuickActionsView token={token} workspaceId={workspaceId} />
        ) : screen === "leads" && data ? (
          <LeadsPanel
            data={data as Leads}
            token={token}
            workspaceId={workspaceId}
            filters={leadFilters}
            onFiltersChange={setLeadFilters}
            onChanged={() => void load()}
          />
        ) : null}
      </main>
    </div>
  );
}

function LeadsPanel({
  data,
  token,
  workspaceId,
  filters,
  onFiltersChange,
  onChanged,
}: {
  data: Leads;
  token: string;
  workspaceId: string;
  filters: { search: string; status: string; source: string };
  onFiltersChange: (next: { search: string; status: string; source: string }) => void;
  onChanged: () => void;
}) {
  const [search, setSearch] = useState(filters.search);
  const [status, setStatus] = useState(filters.status);
  const [source, setSource] = useState(filters.source);
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [form, setForm] = useState({
    name: "",
    company: "",
    email: "",
    source: "manual",
    status: "new",
    notes: "",
    follow_up_date: "",
  });

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setFormError(null);
    try {
      await createLead(token, workspaceId, {
        name: form.name,
        company: form.company || null,
        email: form.email,
        source: form.source,
        status: form.status,
        notes: form.notes || null,
        follow_up_date: form.follow_up_date || null,
      });
      setForm({
        name: "",
        company: "",
        email: "",
        source: "manual",
        status: "new",
        notes: "",
        follow_up_date: "",
      });
      onChanged();
    } catch (err) {
      setFormError(err instanceof Error ? err.message : "Failed to create lead");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <form
        className="ops-toolbar"
        onSubmit={(e) => {
          e.preventDefault();
          onFiltersChange({ search, status, source });
        }}
      >
        <input
          aria-label="Search leads"
          placeholder="Search name, email, company"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        <select
          aria-label="Filter by status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          <option value="">All statuses</option>
          {LEAD_STATUSES.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
        <input
          aria-label="Filter by source"
          placeholder="Source"
          value={source}
          onChange={(e) => setSource(e.target.value)}
        />
        <button type="submit">Apply filters</button>
      </form>

      <form className="ops-form" onSubmit={(e) => void submit(e)}>
        <h3>Add lead</h3>
        <div className="ops-form__grid">
          <input required placeholder="Name" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input placeholder="Company" value={form.company} onChange={(e) => setForm({ ...form, company: e.target.value })} />
          <input required type="email" placeholder="Email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
          <input placeholder="Source" value={form.source} onChange={(e) => setForm({ ...form, source: e.target.value })} />
          <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
            {LEAD_STATUSES.map((item) => (
              <option key={item} value={item}>{item}</option>
            ))}
          </select>
          <input type="date" value={form.follow_up_date} onChange={(e) => setForm({ ...form, follow_up_date: e.target.value })} />
          <input className="ops-form__wide" placeholder="Notes" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
        </div>
        {formError ? <p className="ops-form__error">{formError}</p> : null}
        <button type="submit" disabled={busy}>{busy ? "Saving…" : "Create lead"}</button>
      </form>

      {data.leads.length === 0 ? (
        <Empty>No leads match the current filters.</Empty>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Company</th>
                <th>Email</th>
                <th>Source</th>
                <th>Status</th>
                <th>Notes</th>
                <th>Follow-up</th>
              </tr>
            </thead>
            <tbody>
              {data.leads.map((lead) => (
                <tr key={lead.id}>
                  <td><strong>{lead.name}</strong></td>
                  <td>{lead.company ?? "—"}</td>
                  <td>{lead.email}</td>
                  <td>{lead.source}</td>
                  <td>
                    <select
                      aria-label={`Status for ${lead.name}`}
                      value={lead.status}
                      onChange={(e) => {
                        void updateLead(token, workspaceId, lead.id, {
                          status: e.target.value,
                        }).then(onChanged);
                      }}
                    >
                      {LEAD_STATUSES.map((item) => (
                        <option key={item} value={item}>{item}</option>
                      ))}
                    </select>
                  </td>
                  <td>{lead.notes ?? "—"}</td>
                  <td>{formatDay(lead.follow_up_date)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="freshness">{data.total} lead(s) · Updated {formatDate(data.generated_at)}</p>
    </>
  );
}
