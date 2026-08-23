import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import ErrorBoundary from "./ErrorBoundary";
import { BusinessManagerMark } from "./BusinessManagerMark";
import { useDialogFocus } from "./useDialogFocus";
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
import {
  HEALTH_COPY,
  aggregateHealth,
  isActivityFeed,
  isAnalyticsData,
  isBillingData,
  isContentCommand,
  isCustomers,
  isDashboardData,
  isExecutiveMode,
  isLeads,
  isLiveLogs,
  isPipelineMonitor,
  isSettingsData,
  isWorkersData,
  type DashboardData,
} from "./dashboardModel";

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
  { id: "dashboard", label: "Home", icon: "dashboard" },
  { id: "workers", label: "AI Workforce", icon: "workers" },
  { id: "pipelines", label: "Content Operations", icon: "pipelines" },
  { id: "review", label: "Human Review", icon: "review" },
  { id: "leads", label: "Opportunities", icon: "leads" },
  { id: "analytics", label: "Business Intelligence", icon: "analytics" },
  { id: "billing", label: "Financial Intelligence", icon: "billing" },
  { id: "customers", label: "Audience", icon: "customers" },
  { id: "mission", label: "Connections", icon: "mission" },
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
      <button className="button button--primary" onClick={retry} type="button">Try again</button>
    </div>
  );
}

function EmptyState({
  icon = "activity",
  title,
  message,
}: {
  icon?: IconName;
  title: string;
  message: string;
}) {
  return (
    <div className="empty-state">
      <span className="empty-icon"><Icon name={icon} size={28} /></span>
      <h3>{title}</h3>
      <p>{message}</p>
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
  const [range, setRange] = useState<"7D" | "30D" | "90D" | "1Y">("30D");
  const priority = { critical: 0, warning: 1, info: 2 } as const;
  const decisionTargets: Record<string, NavKey> = {
    review_required: "review",
    review_waiting: "review",
    failed_jobs: "pipelines",
    pipeline_failed: "pipelines",
    spend_warning: "billing",
    worker_offline: "workers",
    failed_webhooks: "mission",
    queue_backlog: "pipelines",
  };
  const decisions = [...data.alerts.alerts]
    .filter((alert) => ["critical", "warning"].includes(alert.severity))
    .sort((left, right) => priority[left.severity] - priority[right.severity]);
  const departments = [
    ["Scout", "Research and opportunity discovery"],
    ["Strategist", "Business and content recommendations"],
    ["Writer", "Scripts, copy, and content packages"],
    ["Producer", "Generation and render orchestration"],
    ["Compliance", "Policy, rights, and originality checks"],
    ["Chief Auditor", "Independent audit-chain verification"],
    ["Analyst", "Outcome and performance learning"],
  ] as const;
  const realWorkers = data.workers.workers;
  const activeWorkerCount = realWorkers.filter((worker) => ["online", "busy"].includes(worker.status.toLowerCase())).length;

  return (
    <div className="dashboard-home business-home">
      <section className="business-home__intro">
        <div>
          <p className="page-kicker">The Business Manager</p>
          <h2>Home</h2>
          <p>What happened, what it cost, what it made, and what needs your decision.</p>
        </div>
        <span className="live-indicator"><i /> Workspace-backed data</span>
      </section>

      <section className="financial-hero" aria-label="Business profitability">
        <div className="financial-hero__copy">
          <p className="financial-hero__eyebrow">Business performance</p>
          <h3>Is my business making money?</h3>
          <p>Connect your financial data to see profitability.</p>
          <span className="financial-hero__note">Revenue, expenses, net profit, and margin appear only after a connected workspace source is available.</span>
          <div className="financial-range" role="group" aria-label="Financial time range">
            {(["7D", "30D", "90D", "1Y"] as const).map((option) => (
              <button className={range === option ? "financial-range__option financial-range__option--active" : "financial-range__option"} key={option} onClick={() => setRange(option)} type="button">{option}</button>
            ))}
          </div>
        </div>
        <div className="financial-hero__donut" aria-label={`Financial data unavailable for ${range}`}>
          <div className="financial-hero__donut-core">
            <span>Financial data</span>
            <strong>Not connected</strong>
            <small>{range} view</small>
          </div>
        </div>
      </section>

      <section className="business-section what-needs-you" id="active-alerts">
        <SectionHeader
          title="What needs you now"
          detail={decisions.length ? "High-value human decisions and interventions, ordered by severity." : "No high-value human decisions are currently reported by the backend."}
          action={decisions.length ? <button className="text-button" onClick={() => navigate("review")} type="button">Open Human Review</button> : undefined}
        />
        {decisions.length === 0 ? (
          <EmptyState icon="check" title="Nothing needs your decision" message="No review, failure, spend, or connection condition currently requires a founder action." />
        ) : (
          <div className="decision-list">
            {decisions.map((alert) => (
              <button className={`decision-card decision-card--${alert.severity}`} key={alert.key} onClick={() => navigate(decisionTargets[alert.key] ?? "mission")} type="button">
                <span className={`severity-tag severity-tag--${alert.severity}`}>{alert.severity}</span>
                <span className="decision-card__copy"><strong>{alert.title}</strong><small>{alert.message}</small></span>
                {alert.count > 1 ? <b>{alert.count}</b> : <Icon name="arrow" size={16} />}
              </button>
            ))}
          </div>
        )}
      </section>

      <section className="business-section workforce-summary">
        <SectionHeader
          title="AI Workforce"
          detail={`${realWorkers.length} registered worker process${realWorkers.length === 1 ? "" : "es"}; ${activeWorkerCount} currently live. Department capability is shown only when configured.`}
          action={<button className="text-button" onClick={() => navigate("workers")} type="button">Open workforce</button>}
        />
        <div className="department-grid">
          {departments.map(([name, responsibility]) => (
            <article className="department-card" key={name}>
              <span className="department-card__state">Not configured</span>
              <h4>{name}</h4>
              <p>{responsibility}</p>
              <small>No workspace role binding or executable capability is configured.</small>
            </article>
          ))}
        </div>
        <div className="workforce-telemetry">
          <div><span>Registered processes</span><strong>{realWorkers.length}</strong></div>
          <div><span>Live processes</span><strong>{activeWorkerCount}</strong></div>
          <div><span>Queue depth</span><strong>{data.pipelines.queue_depth}</strong></div>
          <div><span>Retries recorded</span><strong>{realWorkers.reduce((total, worker) => total + worker.retry_count, 0)}</strong></div>
        </div>
      </section>

      <div className="business-home__signals">
        <section className="surface activity-surface">
          <SectionHeader title="What happened" detail="Backend-recorded activity in this workspace" action={<button className="text-button" onClick={() => navigate("analytics")} type="button">Open activity</button>} />
          <ActivityFeedView data={{ ...data.activity, items: data.activity.items.slice(0, 5) }} />
        </section>
        <section className="surface health-surface">
          <SectionHeader title="System signals" detail="Advanced operational detail" />
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

      <section className="surface quick-surface business-home__controls">
        <SectionHeader title="Advanced operator controls" detail="Existing audited controls remain available; destructive actions require explicit confirmation." />
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
  const drawerRef = useDialogFocus<HTMLElement>(selected !== null, () => setSelected(null));
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
          <aside aria-label="Review details" aria-modal="true" className="review-drawer" onMouseDown={(event) => event.stopPropagation()} ref={drawerRef} role="dialog" tabIndex={-1}>
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
  const [actionError, setActionError] = useState<string | null>(null);
  const [form, setForm] = useState({ name: "", company: "", email: "", source: "manual" });
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setActionError(null);
    try {
      await createLead(token, workspaceId, form);
      setShowForm(false);
      setForm({ name: "", company: "", email: "", source: "manual" });
      refresh();
    } catch (cause) {
      setActionError(cause instanceof Error ? cause.message : "Unable to create the lead.");
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
      {actionError ? <p className="error" role="alert">{actionError}</p> : null}
      {data.leads.length === 0 ? (
        <EmptyState icon="leads" title="No leads yet" message="Add your first lead or connect a source to start tracking your pipeline." />
      ) : (
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
                onChange={(event) => {
                  setActionError(null);
                  void updateLead(token, workspaceId, lead.id, { status: event.target.value })
                    .then(refresh)
                    .catch((cause: unknown) => {
                      setActionError(cause instanceof Error ? cause.message : "Unable to update the lead.");
                    });
                }}
                value={lead.status}
              >
                {LEAD_STATUSES.map((status) => <option key={status} value={status}>{status}</option>)}
              </select>
            </span>
          </div>
        ))}
      </div>
      )}
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
  const [loadedKey, setLoadedKey] = useState<string | null>(null);
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [notifications, setNotifications] = useState<Notifications | null>(null);
  const [reviewCount, setReviewCount] = useState(0);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [healthWorkspaceId, setHealthWorkspaceId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [notificationOpen, setNotificationOpen] = useState(false);
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);
  const [reviewBusy, setReviewBusy] = useState<string | null>(null);
  const [reviewActionError, setReviewActionError] = useState<string | null>(null);
  const requestId = useRef(0);
  const mobileNavRef = useDialogFocus<HTMLElement>(mobileOpen, () => setMobileOpen(false));

  const currentWorkspace = workspaces.find((workspace) => workspace.id === workspaceId);
  const viewKey = `${workspaceId}:${nav}:${missionTab}`;

  useEffect(() => {
    let active = true;
    void listWorkspaces(token)
      .then((rows) => { if (active) setWorkspaces(rows); })
      .catch(() => { if (active) setWorkspaces([]); });
    return () => { active = false; };
  }, [token]);

  useEffect(() => {
    let active = true;
    void getNotifications(token, workspaceId)
      .then((value) => { if (active) setNotifications(value); })
      .catch(() => { if (active) setNotifications(null); });
    void listReviewGates(token, workspaceId)
      .then((gates) => { if (active) setReviewCount(gates.length); })
      .catch(() => { if (active) setReviewCount(0); });
    return () => { active = false; };
  }, [token, workspaceId]);

  useEffect(() => {
    // Dashboard and Settings already fetch health as part of their atomic page
    // load. Other routes fetch it here for the persistent shell footer.
    if (nav === "dashboard" || nav === "settings") return;
    let active = true;
    void getSystemHealth(token, workspaceId)
      .then((value) => {
        if (active) {
          setHealth(value);
          setHealthWorkspaceId(workspaceId);
        }
      })
      .catch(() => {
        if (active) {
          setHealth(null);
          setHealthWorkspaceId(workspaceId);
        }
      });
    return () => { active = false; };
  }, [nav, token, workspaceId]);

  const load = useCallback(async () => {
    const currentRequest = requestId.current + 1;
    const currentViewKey = `${workspaceId}:${nav}:${missionTab}`;
    requestId.current = currentRequest;
    const isCurrent = () => requestId.current === currentRequest;
    setLoading(true);
    setError(null);
    try {
      let next: ViewData;
      if (nav === "dashboard") {
        const [executive, pipelines, alerts, activity, health, customers, workers] = await Promise.all([
          getExecutiveDashboard(token, workspaceId),
          getPipelineMonitor(token, workspaceId),
          getOperationsAlerts(token, workspaceId),
          getActivityFeed(token, workspaceId),
          getSystemHealth(token, workspaceId),
          getCustomers(token, workspaceId),
          getWorkerMonitor(token, workspaceId),
        ]);
        next = { executive, pipelines, alerts, activity, health, customers, workers };
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
        const [healthData, executive] = await Promise.all([getSystemHealth(token, workspaceId), getExecutiveDashboard(token, workspaceId)]);
        next = { health: healthData, executive };
      }
      if (!isCurrent()) return;
      setData(next);
      setLoadedKey(currentViewKey);
      if (nav === "dashboard" && next && "health" in next) {
        setHealth((next as DashboardData).health);
        setHealthWorkspaceId(workspaceId);
      } else if (nav === "settings" && next && "health" in next) {
        setHealth((next as { health: SystemHealth }).health);
        setHealthWorkspaceId(workspaceId);
      }
    } catch (cause) {
      if (!isCurrent()) return;
      setData(null);
      setLoadedKey(currentViewKey);
      setError(cause instanceof Error ? cause.message : "Unable to load this view");
    } finally {
      if (isCurrent()) setLoading(false);
    }
  }, [nav, missionTab, token, workspaceId]);

  useEffect(() => { void load(); }, [load]);

  const navigate = (next: NavKey) => {
    if (next !== nav) {
      requestId.current += 1;
      setData(null);
      setLoadedKey(null);
      setError(null);
      setLoading(true);
      setMissionTab("overview");
    }
    setNav(next);
    setMobileOpen(false);
  };

  const changeMissionTab = (next: MissionTab) => {
    if (next !== missionTab) {
      requestId.current += 1;
      setData(null);
      setLoadedKey(null);
      setError(null);
      setLoading(true);
      setMissionTab(next);
    }
  };

  const navigateToMissionTab = (next: MissionTab) => {
    requestId.current += 1;
    setData(null);
    setLoadedKey(null);
    setError(null);
    setLoading(next !== "assistant");
    setNav("mission");
    setMissionTab(next);
    setMobileOpen(false);
  };

  const title = NAV.find((item) => item.id === nav)?.label ?? "Dashboard";
  const awaitingReviews = Array.isArray(data) ? data.filter((gate) => gate.status === "awaiting") : [];
  const notificationCount = notifications?.notifications.length ?? 0;
  const displayedHealth = healthWorkspaceId === workspaceId ? health : null;
  const healthLevel = aggregateHealth(displayedHealth);

  const decide = async (gate: ReviewGate, approved: boolean) => {
    setReviewBusy(gate.id);
    setReviewActionError(null);
    try {
      await decideReviewGate(token, workspaceId, gate.id, approved);
      await load();
    } catch (cause) {
      setReviewActionError(cause instanceof Error ? cause.message : "Unable to save the review decision.");
    } finally {
      setReviewBusy(null);
    }
  };

  const renderView = () => {
    if (error) return <ErrorState error={error} retry={() => void load()} />;

    // Review Queue drives its own list off the shared review fetch and always
    // renders (loading gate below only applies to data-backed views).
    if (nav === "review") {
      if (loading || loadedKey !== viewKey) return <Loading />;
      return (
        <>
          {reviewActionError ? <p className="error" role="alert">{reviewActionError}</p> : null}
          <ReviewQueue busy={reviewBusy} gates={awaitingReviews} onDecision={decide} workspaceName={currentWorkspace?.name ?? "Current workspace"} />
        </>
      );
    }

    // The AI assistant manages its own request lifecycle and needs no view data.
    if (nav === "mission" && missionTab === "assistant") {
      return <AssistantPanel token={token} workspaceId={workspaceId} />;
    }

    // Every other view is data-backed: show the loading gate until the fetch
    // for the *current* route resolves with a matching payload shape. This is
    // what prevents stale-data crashes on navigation.
    if (loading) return <Loading />;
    if (loadedKey !== viewKey) return <Loading />;

    if (nav === "dashboard") {
      if (isDashboardData(data)) return <DashboardHome data={data} navigate={navigate} token={token} workspaceId={workspaceId} />;
      return <Loading />;
    }
    if (nav === "mission") {
      if (missionTab === "overview") return isExecutiveMode(data) ? <ExecutiveModeView data={data} /> : <Loading />;
      if (missionTab === "timeline") return isActivityFeed(data) ? <UniversalTimelineView data={data} /> : <Loading />;
      if (missionTab === "logs") return isLiveLogs(data) ? <LiveLogsView initial={data} token={token} workspaceId={workspaceId} /> : <Loading />;
      if (missionTab === "content") return isContentCommand(data) ? <ContentCommandView data={data} /> : <Loading />;
      return <Loading />;
    }
    if (nav === "pipelines") {
      if (!isPipelineMonitor(data)) return <Loading />;
      if (data.pipelines.length === 0) {
        return (
          <div className="stack">
            <PipelinesView data={data} />
            <EmptyState icon="pipelines" title="No active pipelines" message="Pipeline runs will appear here once content jobs start moving through the system." />
          </div>
        );
      }
      return <PipelinesView data={data} />;
    }
    if (nav === "workers") {
      if (!isWorkersData(data)) return <Loading />;
      if (data.monitor.workers.length === 0) {
        return <EmptyState icon="workers" title="No workers registered" message="Connect a worker to this workspace to start processing jobs." />;
      }
      return (
        <div className="stack">
          <WorkersView data={data.monitor} />
          <section className="surface">
            <SectionHeader title="Worker timeline" detail="Execution history, failures and retry performance" />
            <WorkerTimelineView data={data.timeline} />
          </section>
        </div>
      );
    }
    if (nav === "customers") {
      if (!isCustomers(data)) return <Loading />;
      if (data.customers.length === 0) {
        return <EmptyState icon="customers" title="No customers yet" message="Customer workspaces will appear here as they sign up and subscribe." />;
      }
      return <CustomersView data={data} />;
    }
    if (nav === "leads") {
      if (!isLeads(data)) return <Loading />;
      return <LeadsView data={data} refresh={() => void load()} token={token} workspaceId={workspaceId} />;
    }
    if (nav === "analytics") {
      if (!isAnalyticsData(data)) return <Loading />;
      return (
        <div className="stack">
          <InsightsView data={data.insights} />
          <section className="surface"><SectionHeader title="Activity stream" /><ActivityFeedView data={data.activity} /></section>
          <GitHubSummary data={data.github} />
        </div>
      );
    }
    if (nav === "billing") {
      if (!isBillingData(data)) return <Loading />;
      return <BillingView cost={data.cost} spend={data.spend} />;
    }
    if (nav === "settings") {
      if (!isSettingsData(data)) return <Loading />;
      return (
        <div className="settings-grid">
          <section className="surface"><SectionHeader title="System health" detail="Environment and service readiness" /><SystemHealthView data={data.health} /></section>
          <section className="surface deployment-card">
            <SectionHeader title="Deployment" detail="Current release metadata" />
            <dl>
              <div><dt>CI status</dt><dd><Status value={data.executive.deployment.ci_status} /></dd></div>
              <div><dt>Branch</dt><dd><code>{data.executive.deployment.git_branch ?? "Unavailable"}</code></dd></div>
              <div><dt>Commit</dt><dd><code>{data.executive.deployment.commit_sha?.slice(0, 12) ?? "Unavailable"}</code></dd></div>
              <div><dt>Deployed</dt><dd>{formatDate(data.executive.deployment.deployed_at)}</dd></div>
            </dl>
          </section>
        </div>
      );
    }
    return <Loading />;
  };

  return (
    <div className="lumora-shell">
      <CommandPalette navigate={(target) => {
        if (target === "logs") {
          navigateToMissionTab("logs");
          return;
        }
        const mapping: Record<string, NavKey> = {
          actions: "dashboard",
          executive: "dashboard",
          pipelines: "pipelines",
          workers: "workers",
          "worker-timeline": "workers",
          customers: "customers",
          leads: "leads",
          spend: "billing",
          alerts: "mission",
        };
        navigate(mapping[target] ?? "mission");
      }} token={token} workspaceId={workspaceId} />
      <aside
        aria-label={mobileOpen ? "Mobile navigation" : undefined}
        aria-modal={mobileOpen ? "true" : undefined}
        className={mobileOpen ? "lumora-sidebar lumora-sidebar--open" : "lumora-sidebar"}
        ref={mobileNavRef}
        role={mobileOpen ? "dialog" : undefined}
        tabIndex={-1}
      >
        <div className="brand">
          <BusinessManagerMark className="brand-mark" />
          <div className="brand-copy"><strong>The Business Manager</strong><small>Business Operating System</small></div>
          <button aria-label="Close navigation" className="mobile-close" onClick={() => setMobileOpen(false)} type="button"><Icon name="close" /></button>
        </div>
        <nav aria-label="Primary navigation">
          <p>Business</p>
          {NAV.slice(0, 2).map((item) => (
            <button className={nav === item.id ? "side-link side-link--active" : "side-link"} key={item.id} onClick={() => navigate(item.id)} type="button">
              <Icon name={item.icon} /><span>{item.label}</span>
            </button>
          ))}
          <p>Content</p>
          {NAV.slice(2, 4).map((item) => (
            <button className={nav === item.id ? "side-link side-link--active" : "side-link"} key={item.id} onClick={() => navigate(item.id)} type="button">
              <Icon name={item.icon} /><span>{item.label}</span>
              {item.id === "review" && reviewCount > 0 ? <b>{reviewCount}</b> : null}
            </button>
          ))}
          <p>Intelligence</p>
          {NAV.slice(4, 8).map((item) => (
            <button className={nav === item.id ? "side-link side-link--active" : "side-link"} key={item.id} onClick={() => navigate(item.id)} type="button">
              <Icon name={item.icon} /><span>{item.label}</span>
            </button>
          ))}
          <p>System</p>
          {NAV.slice(8).map((item) => (
            <button className={nav === item.id ? "side-link side-link--active" : "side-link"} key={item.id} onClick={() => navigate(item.id)} type="button">
              <Icon name={item.icon} /><span>{item.label}</span>
            </button>
          ))}
        </nav>
        <button
          className="sidebar-foot"
          onClick={() => navigate("settings")}
          title="View system health"
          type="button"
        >
          <span className={`status-orb status-orb--${HEALTH_COPY[healthLevel].orb}`} />
          <div>
            <strong>{HEALTH_COPY[healthLevel].label}</strong>
            <small>{displayedHealth ? `Updated ${relativeTime(displayedHealth.generated_at)}` : "Live service status"}</small>
          </div>
        </button>
      </aside>
      {mobileOpen ? <button aria-label="Close navigation backdrop" className="mobile-backdrop" onClick={() => setMobileOpen(false)} type="button" /> : null}

      <div className="lumora-workspace">
        <header className="topbar">
          <div className="topbar-identity">
            <button aria-label="Open navigation" className="mobile-menu" onClick={() => setMobileOpen(true)} type="button"><Icon name="menu" /></button>
            <div className="mobile-brand" aria-label="The Business Manager">
              <BusinessManagerMark className="mobile-brand__mark" />
              <span><strong>The Business Manager</strong><small>Business Operating System</small></span>
            </div>
          </div>
          <div className="topbar-utilities">
            <label className="workspace-switcher">
              <span className="workspace-avatar">{(currentWorkspace?.name ?? "W").slice(0, 1).toUpperCase()}</span>
              <select aria-label="Workspace" onChange={(event) => onWorkspaceChange(event.target.value)} value={workspaceId}>
                {workspaces.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.name}</option>)}
              </select>
            </label>
          <div className={mobileSearchOpen ? "topbar-search topbar-search--open" : "topbar-search"}>
            <Icon name="search" size={17} />
            <GlobalSearchBar
              onOpen={(type) => {
                setMobileSearchOpen(false);
                if (type === "log") {
                  navigateToMissionTab("logs");
                  return;
                }
                if (type === "content") {
                  navigateToMissionTab("content");
                  return;
                }
                const mapping: Record<string, NavKey> = { customer: "customers", lead: "leads", pipeline: "pipelines", worker: "workers", review: "review", job: "pipelines" };
                navigate(mapping[type] ?? "mission");
              }}
              token={token}
              workspaceId={workspaceId}
            />
          </div>
          <div className="topbar-actions">
            <button
              aria-label="Search"
              aria-expanded={mobileSearchOpen}
              className="icon-button mobile-search-btn"
              onClick={() => setMobileSearchOpen((value) => !value)}
              type="button"
            >
              <Icon name={mobileSearchOpen ? "close" : "search"} />
            </button>
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
              <button aria-label={`Open profile menu for ${email}`} className="profile-button" onClick={() => setProfileOpen((value) => !value)} type="button">
                <span>{email.slice(0, 1).toUpperCase()}</span>
                <div><strong>{email.split("@")[0]}</strong><small>{email}</small></div>
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
          </div>
        </header>

        <main className="lumora-main">
          {nav !== "dashboard" ? (
            <header className="view-header">
              <div><p>The Business Manager / {title}</p><h1>{title}</h1></div>
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
                <button
                  aria-controls={`mission-panel-${id}`}
                  aria-selected={missionTab === id}
                  className={missionTab === id ? "view-tab view-tab--active" : "view-tab"}
                  id={`mission-tab-${id}`}
                  key={id}
                  onClick={() => changeMissionTab(id)}
                  role="tab"
                  type="button"
                >
                  {label}
                </button>
              ))}
            </div>
          ) : null}
          <div
            aria-labelledby={nav === "mission" ? `mission-tab-${missionTab}` : undefined}
            id={nav === "mission" ? `mission-panel-${missionTab}` : undefined}
            role={nav === "mission" ? "tabpanel" : undefined}
          >
            <ErrorBoundary
              resetKeys={[nav, missionTab, workspaceId]}
              fallback={(boundaryError, reset) => (
                <ErrorState
                  error={boundaryError.message || "This screen ran into a problem."}
                  retry={() => { reset(); void load(); }}
                />
              )}
            >
              {renderView()}
            </ErrorBoundary>
          </div>
        </main>
      </div>
    </div>
  );
}
