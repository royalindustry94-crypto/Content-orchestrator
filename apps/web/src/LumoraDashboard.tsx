import {
  useCallback,
  useEffect,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  createLead,
  decideReviewGate,
  getActivityFeed,
  getContentCommand,
  getCostControl,
  getCustomers,
  getExecutiveDashboard,
  getExecutiveInsights,
  getExecutiveMode,
  getGitHubStatus,
  getLeads,
  getLiveLogs,
  getNotifications,
  getOperationsAlerts,
  getPipelineMonitor,
  getSpendDashboard,
  getSystemHealth,
  getUniversalTimeline,
  getWorkerMonitor,
  getWorkerTimeline,
  listReviewGates,
  listWorkspaces,
  updateLead,
  type ActivityFeed,
  type Alerts,
  type ContentCommand,
  type CostControl,
  type Customers,
  type ExecutiveDashboard,
  type ExecutiveInsights,
  type ExecutiveMode,
  type GitHubOut,
  type Leads,
  type LiveLogs,
  type Notifications,
  type PipelineMonitor,
  type ReviewGate,
  type SpendDashboard,
  type SystemHealth,
  type WorkerMonitor,
  type WorkerTimeline,
  type Workspace,
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

type NavKey =
  | "dashboard"
  | "mission"
  | "review"
  | "pipelines"
  | "workers"
  | "customers"
  | "leads"
  | "analytics"
  | "billing"
  | "settings";

type MissionTab = "overview" | "timeline" | "logs" | "assistant" | "content";

type Props = {
  token: string;
  workspaceId: string;
  email: string;
  onWorkspaceChange: (workspaceId: string) => void;
  onSignOut: () => void;
};

type IconName =
  | "dashboard"
  | "mission"
  | "review"
  | "pipelines"
  | "workers"
  | "customers"
  | "leads"
  | "analytics"
  | "billing"
  | "settings"
  | "search"
  | "bell"
  | "chevron"
  | "menu"
  | "close"
  | "arrow"
  | "refresh"
  | "activity"
  | "check"
  | "alert";

const PATHS: Record<IconName, ReactNode> = {
  dashboard: <><rect x="3" y="3" width="7" height="7" rx="2" /><rect x="14" y="3" width="7" height="7" rx="2" /><rect x="3" y="14" width="7" height="7" rx="2" /><rect x="14" y="14" width="7" height="7" rx="2" /></>,
  mission: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3" /></>,
  review: <><path d="M9 11l2 2 4-4" /><path d="M20 12a8 8 0 11-4.8-7.3" /><path d="M16 3h5v5" /></>,
  pipelines: <><path d="M4 5h16M4 12h10M4 19h16" /><circle cx="17" cy="12" r="3" /></>,
  workers: <><rect x="3" y="8" width="18" height="12" rx="3" /><path d="M8 8V5h8v3M8 14h.01M16 14h.01M9 18h6" /></>,
  customers: <><path d="M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 00-3-3.87M16 3.13a4 4 0 010 7.75" /></>,
  leads: <><path d="M4 20h16M6 17V8M12 17V4M18 17v-6" /></>,
  analytics: <><path d="M3 3v18h18" /><path d="M7 15l4-4 3 3 5-7" /></>,
  billing: <><rect x="2" y="5" width="20" height="14" rx="3" /><path d="M2 10h20M6 15h3" /></>,
  settings: <><circle cx="12" cy="12" r="3" /><path d="M19.4 15a1.7 1.7 0 00.34 1.88l.06.06-2.83 2.83-.06-.06A1.7 1.7 0 0015 19.4a1.7 1.7 0 00-1 .6 1.7 1.7 0 00-.4 1.1V21H9v-.09A1.7 1.7 0 007.6 19.4a1.7 1.7 0 00-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 003.6 15a1.7 1.7 0 00-1.6-1H2V10h.09A1.7 1.7 0 003.6 8.6a1.7 1.7 0 00-.34-1.88l-.06-.06 2.83-2.83.06.06A1.7 1.7 0 008 4.6a1.7 1.7 0 001-1.6V3h4v.09a1.7 1.7 0 001.4 1.51 1.7 1.7 0 001.88-.34l.06-.06 2.83 2.83-.06.06A1.7 1.7 0 0020.4 9c.3.61.91 1 1.6 1h.09v4H22a1.7 1.7 0 00-1.6 1z" /></>,
  search: <><circle cx="11" cy="11" r="7" /><path d="M20 20l-4-4" /></>,
  bell: <><path d="M18 8a6 6 0 00-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></>,
  chevron: <path d="M9 18l6-6-6-6" />,
  menu: <path d="M4 7h16M4 12h16M4 17h16" />,
  close: <path d="M6 6l12 12M18 6L6 18" />,
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  refresh: <><path d="M20 11a8 8 0 10-2.3 5.7" /><path d="M20 4v7h-7" /></>,
  activity: <path d="M3 12h4l2-7 4 14 2-7h6" />,
  check: <path d="M5 12l4 4L19 6" />,
  alert: <><path d="M12 3l10 18H2L12 3z" /><path d="M12 9v5M12 18h.01" /></>,
};

function Icon({ name, size = 18 }: { name: IconName; size?: number }) {
  return (
    <svg
      aria-hidden="true"
      className="ui-icon"
      fill="none"
      height={size}
      viewBox="0 0 24 24"
      width={size}
      stroke="currentColor"
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeWidth="1.8"
    >
      {PATHS[name]}
    </svg>
  );
}

const NAV: Array<{ id: NavKey; label: string; icon: IconName }> = [
  { id: "dashboard", label: "Dashboard", icon: "dashboard" },
  { id: "mission", label: "Mission Control", icon: "mission" },
  { id: "review", label: "Review Queue", icon: "review" },
  { id: "pipelines", label: "Pipelines", icon: "pipelines" },
  { id: "workers", label: "Workers", icon: "workers" },
  { id: "customers", label: "Customers", icon: "customers" },
  { id: "leads", label: "Leads", icon: "leads" },
  { id: "analytics", label: "Analytics", icon: "analytics" },
  { id: "billing", label: "Billing", icon: "billing" },
  { id: "settings", label: "Settings", icon: "settings" },
];

function formatDate(value: string | null | undefined): string {
  if (!value) return "Unavailable";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function relativeTime(value: string): string {
  const seconds = Math.round((new Date(value).getTime() - Date.now()) / 1000);
  const formatter = new Intl.RelativeTimeFormat(undefined, { numeric: "auto" });
  if (Math.abs(seconds) < 60) return formatter.format(seconds, "second");
  const minutes = Math.round(seconds / 60);
  if (Math.abs(minutes) < 60) return formatter.format(minutes, "minute");
  const hours = Math.round(minutes / 60);
  if (Math.abs(hours) < 24) return formatter.format(hours, "hour");
  return formatter.format(Math.round(hours / 24), "day");
}

function money(value: string | number | null | undefined): string {
  if (value == null) return "Unavailable";
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(Number(value));
}

function Loading() {
  return (
    <div aria-busy="true" aria-label="Loading" className="loading-grid">
      {Array.from({ length: 6 }, (_, index) => <div className="skeleton" key={index} />)}
    </div>
  );
}

function ErrorState({ error, retry }: { error: string; retry: () => void }) {
  return (
    <div className="error-state" role="alert">
      <Icon name="alert" size={24} />
      <h3>We couldn&apos;t load this view</h3>
      <p>{error}</p>
      <button onClick={retry} type="button">Try again</button>
    </div>
  );
}

function Status({ value }: { value: string }) {
  const normalized = value.toLowerCase();
  const tone = ["online", "healthy", "green", "active", "completed", "published", "won", "trialing"].includes(normalized)
    ? "good"
    : ["failed", "offline", "red", "critical", "lost", "cancelled"].includes(normalized)
      ? "bad"
      : "warn";
  return <span className={`status status--${tone}`}>{value.replaceAll("_", " ")}</span>;
}

function SectionHeader({
  title,
  detail,
  action,
}: {
  title: string;
  detail?: string;
  action?: ReactNode;
}) {
  return (
    <header className="section-header">
      <div>
        <h3>{title}</h3>
        {detail ? <p>{detail}</p> : null}
      </div>
      {action}
    </header>
  );
}

type DashboardData = {
  executive: ExecutiveDashboard;
  pipelines: PipelineMonitor;
  alerts: Alerts;
  activity: ActivityFeed;
  health: SystemHealth;
  customers: Customers;
};

function DashboardHome({
  data,
  token,
  workspaceId,
  navigate,
}: {
  data: DashboardData;
  token: string;
  workspaceId: string;
  navigate: (key: NavKey) => void;
}) {
  const metrics = [
    { label: "Jobs Running", value: data.executive.jobs_running, icon: "activity" as IconName, tone: "violet" },
    { label: "Jobs Completed Today", value: data.pipelines.jobs_completed, icon: "check" as IconName, tone: "green" },
    { label: "Reviews Waiting", value: data.executive.human_reviews_waiting, icon: "review" as IconName, tone: "amber" },
    { label: "Workers Online", value: data.executive.workers_online, icon: "workers" as IconName, tone: "blue" },
    { label: "Spend Today", value: money(data.executive.spend_today_usd), icon: "billing" as IconName, tone: "pink" },
    { label: "Revenue", value: money(data.customers.revenue_mtd_usd), icon: "analytics" as IconName, tone: "green" },
    { label: "Alerts", value: data.alerts.alerts.length, icon: "alert" as IconName, tone: data.alerts.alerts.length ? "red" : "green" },
  ];
  return (
    <div className="dashboard-home">
      <section className="hero-row">
        <div>
          <p className="page-kicker">Operations overview</p>
          <h2>Good {new Date().getHours() < 12 ? "morning" : new Date().getHours() < 18 ? "afternoon" : "evening"}.</h2>
          <p>Here&apos;s what&apos;s happening across your workspace today.</p>
        </div>
        <span className="live-indicator"><i /> Live data</span>
      </section>

      <div className="saas-metrics">
        {metrics.map((metric) => (
          <button
            className={`saas-metric saas-metric--${metric.tone}`}
            key={metric.label}
            onClick={() => {
              if (metric.label === "Reviews Waiting") navigate("review");
              else if (metric.label === "Workers Online") navigate("workers");
              else if (metric.label === "Spend Today" || metric.label === "Revenue") navigate("billing");
              else if (metric.label === "Alerts") navigate("mission");
              else navigate("pipelines");
            }}
            type="button"
          >
            <span className="metric-icon"><Icon name={metric.icon} /></span>
            <span>{metric.label}</span>
            <strong>{metric.value}</strong>
            <small>View details <Icon name="arrow" size={13} /></small>
          </button>
        ))}
      </div>

      <div className="dashboard-columns">
        <section className="surface activity-surface">
          <SectionHeader
            title="Recent Activity"
            detail="Latest changes across your operations"
            action={<button className="text-button" onClick={() => navigate("analytics")} type="button">View all</button>}
          />
          <ActivityFeedView data={{ ...data.activity, items: data.activity.items.slice(0, 6) }} />
        </section>
        <section className="surface health-surface">
          <SectionHeader title="System Health" detail="Live service status" />
          <div className="health-list">
            {data.health.indicators.map((indicator) => (
              <div className="health-row" key={indicator.key}>
                <span className={`health-dot health-dot--${indicator.status}`} />
                <div><strong>{indicator.label}</strong><small>{indicator.detail}</small></div>
                <Status value={indicator.status} />
              </div>
            ))}
          </div>
        </section>
      </div>

      <section className="surface quick-surface">
        <SectionHeader title="Quick Actions" detail="Common operational controls" />
        <QuickActionsView token={token} workspaceId={workspaceId} />
      </section>
    </div>
  );
}

function ReviewQueue({
  gates,
  workspaceName,
  busy,
  onDecision,
}: {
  gates: ReviewGate[];
  workspaceName: string;
  busy: string | null;
  onDecision: (gate: ReviewGate, approved: boolean) => Promise<void>;
}) {
  const [selected, setSelected] = useState<ReviewGate | null>(null);
  useEffect(() => {
    if (selected) {
      const fresh = gates.find((gate) => gate.id === selected.id);
      if (fresh) setSelected(fresh);
    }
  }, [gates]);
  return (
    <>
      <div className="review-summary">
        <div><strong>{gates.length}</strong><span>Awaiting review</span></div>
        <p>Human Review Gate keeps every publish decision in your control.</p>
      </div>
      {gates.length === 0 ? (
        <div className="empty-state">
          <span className="empty-icon"><Icon name="check" size={28} /></span>
          <h3>You&apos;re all caught up</h3>
          <p>No content is waiting at the Human Review Gate.</p>
        </div>
      ) : (
        <div className="review-grid">
          {gates.map((gate) => (
            <article className="review-card" key={gate.id}>
              <header>
                <Status value={gate.status} />
                <time dateTime={gate.requested_at}>{relativeTime(gate.requested_at)}</time>
              </header>
              <h3>{gate.topic}</h3>
              <div className="review-meta">
                <span><b>Pipeline</b><code>{gate.pipeline_run_id.slice(0, 8)}</code></span>
                <span><b>Workspace</b>{workspaceName}</span>
                <span><b>Stage</b>{gate.stage.replaceAll("_", " ")}</span>
              </div>
              <footer>
                <button className="button button--approve" disabled={busy === gate.id} onClick={() => void onDecision(gate, true)} type="button">
                  <Icon name="check" size={15} /> Approve
                </button>
                <button className="button button--reject" disabled={busy === gate.id} onClick={() => void onDecision(gate, false)} type="button">
                  <Icon name="close" size={15} /> Reject
                </button>
                <button className="button button--open" onClick={() => setSelected(gate)} type="button">Open <Icon name="arrow" size={14} /></button>
              </footer>
            </article>
          ))}
        </div>
      )}
      {selected ? (
        <div className="drawer-backdrop" onMouseDown={() => setSelected(null)} role="presentation">
          <aside aria-label="Review details" aria-modal="true" className="review-drawer" onMouseDown={(event) => event.stopPropagation()} role="dialog">
            <header className="drawer-header">
              <div><p>Human Review Gate</p><h2>{selected.topic}</h2></div>
              <button aria-label="Close review details" onClick={() => setSelected(null)} type="button"><Icon name="close" /></button>
            </header>
            <div className="drawer-meta">
              <span><b>Status</b><Status value={selected.status} /></span>
              <span><b>Created</b>{formatDate(selected.requested_at)}</span>
              <span><b>Pipeline</b><code>{selected.pipeline_run_id}</code></span>
              <span><b>Workspace</b>{workspaceName}</span>
            </div>
            <div className="content-preview">
              {selected.script_hook ? <section><h4>Hook</h4><p>{selected.script_hook}</p></section> : null}
              {selected.script_body ? <section><h4>Script</h4><p>{selected.script_body}</p></section> : null}
              {selected.script_cta ? <section><h4>Call to action</h4><p>{selected.script_cta}</p></section> : null}
              {!selected.script_hook && !selected.script_body && !selected.script_cta ? <p>No text content was attached to this review.</p> : null}
            </div>
            {selected.status === "awaiting" ? (
              <footer className="drawer-actions">
                <button className="button button--reject" disabled={busy === selected.id} onClick={() => void onDecision(selected, false)} type="button">Reject</button>
                <button className="button button--approve" disabled={busy === selected.id} onClick={() => void onDecision(selected, true)} type="button">Approve content</button>
              </footer>
            ) : null}
          </aside>
        </div>
      ) : null}
    </>
  );
}

function PipelinesView({ data }: { data: PipelineMonitor }) {
  return (
    <>
      <div className="compact-metrics">
        <article><span>Active</span><strong>{data.active_pipelines}</strong></article>
        <article><span>Waiting</span><strong>{data.jobs_waiting}</strong></article>
        <article><span>Completed</span><strong>{data.jobs_completed}</strong></article>
        <article><span>Failed</span><strong>{data.jobs_failed}</strong></article>
      </div>
      <div className="data-table">
        <div className="data-row data-row--head"><span>Pipeline</span><span>Status</span><span>Current stage</span><span>Last update</span></div>
        {data.pipelines.map((pipeline) => (
          <div className="data-row" key={pipeline.id}>
            <span><code>{pipeline.id.slice(0, 12)}</code></span>
            <span><Status value={pipeline.status} /></span>
            <span>{pipeline.current_stage.replaceAll("_", " ")}</span>
            <span>{relativeTime(pipeline.updated_at)}</span>
          </div>
        ))}
      </div>
    </>
  );
}

function WorkersView({ data }: { data: WorkerMonitor }) {
  return (
    <div className="worker-grid">
      {data.workers.map((worker) => (
        <article className="worker-card" key={worker.id}>
          <header>
            <span className="worker-avatar"><Icon name="workers" /></span>
            <div><h3>{worker.name}</h3><Status value={worker.status} /></div>
          </header>
          <div className="worker-stats">
            <span><b>{worker.queue}</b>Queue</span>
            <span><b>{worker.jobs_completed_today}</b>Completed</span>
            <span><b>{worker.jobs_failed_today}</b>Failed</span>
          </div>
          <p><span>Current task</span>{worker.current_task ?? worker.current_job ?? "Idle"}</p>
          <small>Heartbeat {formatDate(worker.last_heartbeat_at)}</small>
        </article>
      ))}
    </div>
  );
}

function CustomersView({ data }: { data: Customers }) {
  return (
    <>
      <div className="compact-metrics">
        <article><span>Active</span><strong>{data.active_users}</strong></article>
        <article><span>Paying</span><strong>{data.paying_users}</strong></article>
        <article><span>Trial</span><strong>{data.trial_users}</strong></article>
        <article><span>Revenue MTD</span><strong>{money(data.revenue_mtd_usd)}</strong></article>
      </div>
      <div className="data-table">
        <div className="data-row data-row--head"><span>Workspace</span><span>Plan</span><span>Status</span><span>Members</span></div>
        {data.customers.map((customer) => (
          <div className="data-row" key={customer.workspace_id}>
            <span><strong>{customer.name}</strong></span>
            <span>{customer.plan}</span>
            <span><Status value={customer.subscription_status} /></span>
            <span>{customer.member_count}</span>
          </div>
        ))}
      </div>
    </>
  );
}

const LEAD_STATUSES = ["new", "contacted", "qualified", "negotiation", "won", "lost", "nurturing"];

function LeadsView({
  data,
  token,
  workspaceId,
  refresh,
}: {
  data: Leads;
  token: string;
  workspaceId: string;
  refresh: () => void;
}) {
  const [showForm, setShowForm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ name: "", company: "", email: "", source: "manual" });
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    try {
      await createLead(token, workspaceId, form);
      setShowForm(false);
      setForm({ name: "", company: "", email: "", source: "manual" });
      refresh();
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <div className="view-actions">
        <p>{data.total} leads in this workspace</p>
        <button className="button button--primary" onClick={() => setShowForm((value) => !value)} type="button">{showForm ? "Cancel" : "Add lead"}</button>
      </div>
      {showForm ? (
        <form className="inline-form" onSubmit={(event) => void submit(event)}>
          <input aria-label="Lead name" onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Name" required value={form.name} />
          <input aria-label="Lead company" onChange={(event) => setForm({ ...form, company: event.target.value })} placeholder="Company" value={form.company} />
          <input aria-label="Lead email" onChange={(event) => setForm({ ...form, email: event.target.value })} placeholder="Email" required type="email" value={form.email} />
          <input aria-label="Lead source" onChange={(event) => setForm({ ...form, source: event.target.value })} placeholder="Source" value={form.source} />
          <button className="button button--primary" disabled={busy} type="submit">{busy ? "Saving…" : "Save lead"}</button>
        </form>
      ) : null}
      <div className="data-table leads-table">
        <div className="data-row data-row--head"><span>Lead</span><span>Company</span><span>Source</span><span>Status</span></div>
        {data.leads.map((lead) => (
          <div className="data-row" key={lead.id}>
            <span><strong>{lead.name}</strong><small>{lead.email}</small></span>
            <span>{lead.company ?? "—"}</span>
            <span>{lead.source}</span>
            <span>
              <select
                aria-label={`Status for ${lead.name}`}
                onChange={(event) => void updateLead(token, workspaceId, lead.id, { status: event.target.value }).then(refresh)}
                value={lead.status}
              >
                {LEAD_STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
              </select>
            </span>
          </div>
        ))}
      </div>
    </>
  );
}

function BillingView({ spend, cost }: { spend: SpendDashboard; cost: CostControl }) {
  return (
    <>
      <div className="compact-metrics">
        <article><span>Spend today</span><strong>{money(spend.today_usd)}</strong></article>
        <article><span>Spend this month</span><strong>{money(spend.month_usd)}</strong></article>
        <article><span>Daily remaining</span><strong>{money(spend.budget_remaining_daily_usd)}</strong></article>
        <article><span>Projected month end</span><strong>{money(cost.projected_month_end_usd)}</strong></article>
      </div>
      <section className="surface"><SectionHeader title="Cost control" detail="Committed spend and budget safeguards" /><CostControlView data={cost} /></section>
    </>
  );
}

function GitHubSummary({ data }: { data: GitHubOut }) {
  return (
    <section className="surface">
      <SectionHeader
        title="Engineering delivery"
        detail={data.available ? data.repository ?? "Connected repository" : data.unavailable_reason ?? "GitHub unavailable"}
      />
      <div className="compact-metrics">
        <article><span>Open pull requests</span><strong>{data.open_pull_requests.length}</strong></article>
        <article><span>Failed actions</span><strong>{data.failed_actions.length}</strong></article>
        <article><span>Recent commits</span><strong>{data.latest_commits.length}</strong></article>
        <article><span>Branch CI</span><strong><Status value={data.branch_status.ci_status} /></strong></article>
      </div>
    </section>
  );
}

type ViewData =
  | DashboardData
  | ExecutiveMode
  | ActivityFeed
  | LiveLogs
  | ContentCommand
  | ReviewGate[]
  | PipelineMonitor
  | { monitor: WorkerMonitor; timeline: WorkerTimeline }
  | Customers
  | Leads
  | { insights: ExecutiveInsights; activity: ActivityFeed; github: GitHubOut }
  | { spend: SpendDashboard; cost: CostControl }
  | { health: SystemHealth; executive: ExecutiveDashboard }
  | null;

export default function LumoraDashboard({
  token,
  workspaceId,
  email,
  onWorkspaceChange,
  onSignOut,
}: Props) {
  const [nav, setNav] = useState<NavKey>("dashboard");
  const [missionTab, setMissionTab] = useState<MissionTab>("overview");
  const [data, setData] = useState<ViewData>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [notifications, setNotifications] = useState<Notifications | null>(null);
  const [reviewCount, setReviewCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [notificationOpen, setNotificationOpen] = useState(false);
  const [reviewBusy, setReviewBusy] = useState<string | null>(null);

  const currentWorkspace = workspaces.find((workspace) => workspace.id === workspaceId);

  useEffect(() => {
    void listWorkspaces(token).then(setWorkspaces);
  }, [token]);

  useEffect(() => {
    void getNotifications(token, workspaceId).then(setNotifications).catch(() => setNotifications(null));
    void listReviewGates(token, workspaceId)
      .then((gates) => setReviewCount(gates.length))
      .catch(() => setReviewCount(0));
  }, [token, workspaceId]);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      let next: ViewData;
      if (nav === "dashboard") {
        const [executive, pipelines, alerts, activity, health, customers] = await Promise.all([
          getExecutiveDashboard(token, workspaceId),
          getPipelineMonitor(token, workspaceId),
          getOperationsAlerts(token, workspaceId),
          getActivityFeed(token, workspaceId),
          getSystemHealth(token, workspaceId),
          getCustomers(token, workspaceId),
        ]);
        next = { executive, pipelines, alerts, activity, health, customers };
      } else if (nav === "mission") {
        if (missionTab === "overview") next = await getExecutiveMode(token, workspaceId);
        else if (missionTab === "timeline") next = await getUniversalTimeline(token, workspaceId);
        else if (missionTab === "logs") next = await getLiveLogs(token, workspaceId);
        else if (missionTab === "content") next = await getContentCommand(token, workspaceId);
        else next = null;
      } else if (nav === "review") next = await listReviewGates(token, workspaceId, "all");
      else if (nav === "pipelines") next = await getPipelineMonitor(token, workspaceId);
      else if (nav === "workers") {
        const [monitor, timeline] = await Promise.all([
          getWorkerMonitor(token, workspaceId),
          getWorkerTimeline(token, workspaceId),
        ]);
        next = { monitor, timeline };
      }
      else if (nav === "customers") next = await getCustomers(token, workspaceId);
      else if (nav === "leads") next = await getLeads(token, workspaceId);
      else if (nav === "analytics") {
        const [insights, activity, github] = await Promise.all([
          getExecutiveInsights(token, workspaceId),
          getActivityFeed(token, workspaceId),
          getGitHubStatus(token, workspaceId),
        ]);
        next = { insights, activity, github };
      } else if (nav === "billing") {
        const [spend, cost] = await Promise.all([getSpendDashboard(token, workspaceId), getCostControl(token, workspaceId)]);
        next = { spend, cost };
      } else {
        const [health, executive] = await Promise.all([getSystemHealth(token, workspaceId), getExecutiveDashboard(token, workspaceId)]);
        next = { health, executive };
      }
      setData(next);
    } catch (cause) {
      setData(null);
      setError(cause instanceof Error ? cause.message : "Unable to load this view");
    } finally {
      setLoading(false);
    }
  }, [nav, missionTab, token, workspaceId]);

  useEffect(() => { void load(); }, [load]);

  const navigate = (next: NavKey) => {
    setNav(next);
    setMobileOpen(false);
  };

  const title = NAV.find((item) => item.id === nav)?.label ?? "Dashboard";
  const awaitingReviews = Array.isArray(data) ? data.filter((gate) => gate.status === "awaiting") : [];
  const notificationCount = notifications?.notifications.length ?? 0;

  const decide = async (gate: ReviewGate, approved: boolean) => {
    setReviewBusy(gate.id);
    try {
      await decideReviewGate(token, workspaceId, gate.id, approved);
      await load();
    } finally {
      setReviewBusy(null);
    }
  };

  const renderView = () => {
    if (error) return <ErrorState error={error} retry={() => void load()} />;
    if (loading) return <Loading />;
    if (nav === "dashboard" && data) return <DashboardHome data={data as DashboardData} navigate={navigate} token={token} workspaceId={workspaceId} />;
    if (nav === "mission") {
      if (missionTab === "assistant") return <AssistantPanel token={token} workspaceId={workspaceId} />;
      if (missionTab === "overview" && data) return <ExecutiveModeView data={data as ExecutiveMode} />;
      if (missionTab === "timeline" && data) return <UniversalTimelineView data={data as ActivityFeed} />;
      if (missionTab === "logs" && data) return <LiveLogsView initial={data as LiveLogs} token={token} workspaceId={workspaceId} />;
      if (missionTab === "content" && data) return <ContentCommandView data={data as ContentCommand} />;
    }
    if (nav === "review") return <ReviewQueue busy={reviewBusy} gates={awaitingReviews} onDecision={decide} workspaceName={currentWorkspace?.name ?? "Current workspace"} />;
    if (nav === "pipelines" && data) return <PipelinesView data={data as PipelineMonitor} />;
    if (nav === "workers" && data) {
      const workers = data as { monitor: WorkerMonitor; timeline: WorkerTimeline };
      return (
        <div className="stack">
          <WorkersView data={workers.monitor} />
          <section className="surface">
            <SectionHeader title="Worker timeline" detail="Execution history, failures and retry performance" />
            <WorkerTimelineView data={workers.timeline} />
          </section>
        </div>
      );
    }
    if (nav === "customers" && data) return <CustomersView data={data as Customers} />;
    if (nav === "leads" && data) return <LeadsView data={data as Leads} refresh={() => void load()} token={token} workspaceId={workspaceId} />;
    if (nav === "analytics" && data) {
      const analytics = data as { insights: ExecutiveInsights; activity: ActivityFeed; github: GitHubOut };
      return (
        <div className="stack">
          <InsightsView data={analytics.insights} />
          <section className="surface"><SectionHeader title="Activity stream" /><ActivityFeedView data={analytics.activity} /></section>
          <GitHubSummary data={analytics.github} />
        </div>
      );
    }
    if (nav === "billing" && data) {
      const billing = data as { spend: SpendDashboard; cost: CostControl };
      return <BillingView cost={billing.cost} spend={billing.spend} />;
    }
    if (nav === "settings" && data) {
      const settings = data as { health: SystemHealth; executive: ExecutiveDashboard };
      return (
        <div className="settings-grid">
          <section className="surface"><SectionHeader title="System health" detail="Environment and service readiness" /><SystemHealthView data={settings.health} /></section>
          <section className="surface deployment-card">
            <SectionHeader title="Deployment" detail="Current release metadata" />
            <dl>
              <div><dt>CI status</dt><dd><Status value={settings.executive.deployment.ci_status} /></dd></div>
              <div><dt>Branch</dt><dd><code>{settings.executive.deployment.git_branch ?? "Unavailable"}</code></dd></div>
              <div><dt>Commit</dt><dd><code>{settings.executive.deployment.commit_sha?.slice(0, 12) ?? "Unavailable"}</code></dd></div>
              <div><dt>Deployed</dt><dd>{formatDate(settings.executive.deployment.deployed_at)}</dd></div>
            </dl>
          </section>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="lumora-shell">
      <CommandPalette navigate={(target) => {
        const mapping: Record<string, NavKey> = { executive: "dashboard", pipelines: "pipelines", workers: "workers", customers: "customers", leads: "leads", spend: "billing", alerts: "mission" };
        navigate(mapping[target] ?? "mission");
      }} token={token} workspaceId={workspaceId} />
      <aside className={mobileOpen ? "lumora-sidebar lumora-sidebar--open" : "lumora-sidebar"}>
        <div className="brand">
          <span className="brand-mark">L</span>
          <div><strong>Lumora</strong><small>Mission Control</small></div>
          <button aria-label="Close navigation" className="mobile-close" onClick={() => setMobileOpen(false)} type="button"><Icon name="close" /></button>
        </div>
        <nav aria-label="Primary navigation">
          <p>Workspace</p>
          {NAV.slice(0, 5).map((item) => (
            <button className={nav === item.id ? "side-link side-link--active" : "side-link"} key={item.id} onClick={() => navigate(item.id)} type="button">
              <Icon name={item.icon} /><span>{item.label}</span>
              {item.id === "review" && reviewCount > 0 ? <b>{reviewCount}</b> : null}
            </button>
          ))}
          <p>Business</p>
          {NAV.slice(5, 9).map((item) => (
            <button className={nav === item.id ? "side-link side-link--active" : "side-link"} key={item.id} onClick={() => navigate(item.id)} type="button">
              <Icon name={item.icon} /><span>{item.label}</span>
            </button>
          ))}
          <p>System</p>
          {NAV.slice(9).map((item) => (
            <button className={nav === item.id ? "side-link side-link--active" : "side-link"} key={item.id} onClick={() => navigate(item.id)} type="button">
              <Icon name={item.icon} /><span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          <span className="status-orb" /><div><strong>All systems operational</strong><small>Updated just now</small></div>
        </div>
      </aside>
      {mobileOpen ? <button aria-label="Close navigation backdrop" className="mobile-backdrop" onClick={() => setMobileOpen(false)} type="button" /> : null}

      <div className="lumora-workspace">
        <header className="topbar">
          <button aria-label="Open navigation" className="mobile-menu" onClick={() => setMobileOpen(true)} type="button"><Icon name="menu" /></button>
          <label className="workspace-switcher">
            <span className="workspace-avatar">{(currentWorkspace?.name ?? "W").slice(0, 1).toUpperCase()}</span>
            <select aria-label="Workspace" onChange={(event) => onWorkspaceChange(event.target.value)} value={workspaceId}>
              {workspaces.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.name}</option>)}
            </select>
          </label>
          <div className="topbar-search">
            <Icon name="search" size={17} />
            <GlobalSearchBar
              onOpen={(type) => {
                const mapping: Record<string, NavKey> = { customer: "customers", lead: "leads", pipeline: "pipelines", worker: "workers", review: "review", job: "pipelines", content: "mission", log: "mission" };
                navigate(mapping[type] ?? "mission");
              }}
              token={token}
              workspaceId={workspaceId}
            />
          </div>
          <div className="topbar-actions">
            <div className="popover-anchor">
              <button aria-label="Notifications" className="icon-button" onClick={() => setNotificationOpen((value) => !value)} type="button">
                <Icon name="bell" />
                {notificationCount ? <i>{notificationCount}</i> : null}
              </button>
              {notificationOpen ? (
                <div className="top-popover notifications-popover">
                  <SectionHeader title="Notifications" />
                  {notifications?.notifications.slice(0, 4).map((item) => (
                    <button key={item.key} onClick={() => { setNotificationOpen(false); navigate("mission"); }} type="button">
                      <span className={`health-dot health-dot--${item.severity === "critical" ? "red" : "amber"}`} />
                      <span><strong>{item.title}</strong><small>{item.message}</small></span>
                    </button>
                  ))}
                  {!notificationCount ? <p>No active notifications.</p> : null}
                </div>
              ) : null}
            </div>
            <div className="popover-anchor">
              <button className="profile-button" onClick={() => setProfileOpen((value) => !value)} type="button">
                <span>{email.slice(0, 1).toUpperCase()}</span>
                <div><strong>{email.split("@")[0]}</strong><small>Workspace admin</small></div>
                <Icon name="chevron" size={14} />
              </button>
              {profileOpen ? (
                <div className="top-popover profile-popover">
                  <strong>{email}</strong>
                  <button onClick={() => navigate("settings")} type="button">Account settings</button>
                  <button onClick={onSignOut} type="button">Sign out</button>
                </div>
              ) : null}
            </div>
          </div>
        </header>

        <main className="lumora-main">
          {nav !== "dashboard" ? (
            <header className="view-header">
              <div><p>Lumora / {title}</p><h1>{title}</h1></div>
              <button aria-label="Refresh data" className="icon-button refresh-button" disabled={loading} onClick={() => void load()} type="button"><Icon name="refresh" /></button>
            </header>
          ) : null}
          {nav === "mission" ? (
            <div className="view-tabs" role="tablist">
              {([
                ["overview", "Overview"],
                ["timeline", "Timeline"],
                ["logs", "Live logs"],
                ["assistant", "AI assistant"],
                ["content", "Content"],
              ] as Array<[MissionTab, string]>).map(([id, label]) => (
                <button aria-selected={missionTab === id} key={id} onClick={() => setMissionTab(id)} role="tab" type="button">{label}</button>
              ))}
            </div>
          ) : null}
          {renderView()}
        </main>
      </div>
    </div>
  );
}
