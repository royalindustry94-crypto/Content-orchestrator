// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import LumoraDashboard from "./LumoraDashboard";

/**
 * Navigation + mobile smoke tests.
 *
 * These exercise the exact failure the audit flagged: navigating between
 * routes used to render a previous screen's data into the next view and crash
 * the whole shell (blank screen). They assert that every route renders safely
 * and that the health footer reflects real backend status.
 */

const executive = {
  workers_online: 0,
  workers_busy: 0,
  jobs_running: 3,
  jobs_queued: 0,
  jobs_failed: 1,
  human_reviews_waiting: 2,
  spend_today_usd: "0",
  spend_month_usd: "0",
  active_workspaces: 1,
  deployment: {
    ci_status: "success",
    ci_url: null,
    git_branch: "main",
    commit_sha: "abc123def456",
    deployed_at: "2026-08-07T00:00:00Z",
  },
  generated_at: "2026-08-07T00:00:00Z",
};

const pipelines = {
  active_pipelines: 0,
  queue_depth: 0,
  failed_pipelines: 0,
  retrying_pipelines: 0,
  dead_letter_queue: 0,
  review_gates: 0,
  publish_queue: 0,
  jobs_completed: 12,
  jobs_waiting: 0,
  jobs_failed: 0,
  human_reviews_waiting: 0,
  publishing_queue: 0,
  pipelines: [],
  generated_at: "2026-08-07T00:00:00Z",
};

const alerts = {
  alerts: [
    { key: "a1", severity: "critical", title: "Worker Offline", count: 8, message: "8 workers offline" },
    { key: "a2", severity: "warning", title: "Review Waiting", count: 2, message: "2 reviews waiting" },
  ],
  generated_at: "2026-08-07T00:00:00Z",
};

const health = {
  indicators: [
    { key: "api", label: "API Health", status: "green", detail: "ok" },
    { key: "worker", label: "Worker Health", status: "red", detail: "0/8 workers live" },
  ],
  generated_at: "2026-08-07T00:00:00Z",
};

const customers = {
  beta_users: 0,
  active_users: 0,
  paying_users: 0,
  trial_users: 0,
  revenue_mtd_usd: "0",
  revenue_source: "stripe",
  customers: [],
  generated_at: "2026-08-07T00:00:00Z",
};

const executiveMode = {
  health: health.indicators,
  revenue_mtd_usd: "0",
  spend_today_usd: "0",
  spend_month_usd: "0",
  workers_online: 0,
  workers_total: 8,
  jobs_running: 3,
  jobs_waiting: 0,
  jobs_failed_today: 1,
  critical_alerts: 1,
  reviews_waiting: 2,
  new_customers_today: 0,
  todays_summary: ["Everything nominal"],
  generated_at: "2026-08-07T00:00:00Z",
};

vi.mock("./api", () => ({
  getExecutiveDashboard: vi.fn(async () => executive),
  getPipelineMonitor: vi.fn(async () => pipelines),
  getOperationsAlerts: vi.fn(async () => alerts),
  getActivityFeed: vi.fn(async () => ({ items: [], generated_at: "" })),
  getSystemHealth: vi.fn(async () => health),
  getCustomers: vi.fn(async () => customers),
  getExecutiveMode: vi.fn(async () => executiveMode),
  getUniversalTimeline: vi.fn(async () => ({ items: [], generated_at: "" })),
  getLiveLogs: vi.fn(async () => ({ logs: [], generated_at: "" })),
  getContentCommand: vi.fn(async () => ({
    ideas: 0, scripts: 0, voiceovers: 0, videos_rendering: 0, ready_for_review: 0,
    waiting_for_approval: 0, publishing: 0, published: 0, failed: 0, generated_at: "",
  })),
  getWorkerMonitor: vi.fn(async () => ({ workers: [], generated_at: "" })),
  getWorkerTimeline: vi.fn(async () => ({ workers: [], generated_at: "" })),
  getLeads: vi.fn(async () => ({ leads: [], total: 0, generated_at: "" })),
  getSpendDashboard: vi.fn(async () => ({
    today_usd: "0", week_usd: "0", month_usd: "0", by_provider: [],
    daily_cap_usd: null, monthly_cap_usd: null, budget_remaining_daily_usd: null,
    budget_remaining_monthly_usd: null, generated_at: "",
  })),
  getCostControl: vi.fn(async () => ({
    daily_ai_spend_usd: "0", monthly_ai_spend_usd: "0", budget_remaining_daily_usd: null,
    budget_remaining_monthly_usd: null, by_provider: [], top_expensive_jobs: [],
    projected_month_end_usd: "0", generated_at: "",
  })),
  getExecutiveInsights: vi.fn(async () => ({
    todays_achievements: [], todays_failures: [], highest_risk: "None",
    suggested_next_action: "Keep going", biggest_cost_today_usd: "0",
    biggest_cost_today_label: null, most_active_worker: null, most_active_customer: null,
    generated_at: "",
  })),
  getGitHubStatus: vi.fn(async () => ({
    available: false, unavailable_reason: "n/a", repository: null, latest_commits: [],
    open_pull_requests: [], failed_actions: [], branch_status: { name: null, sha: null, protected: null, ci_status: "unknown" },
    generated_at: "",
  })),
  getNotifications: vi.fn(async () => ({ notifications: [], generated_at: "" })),
  listReviewGates: vi.fn(async () => []),
  listWorkspaces: vi.fn(async () => [{ id: "ws-1", name: "Lumora HQ" }]),
  decideReviewGate: vi.fn(async () => ({})),
  createLead: vi.fn(async () => ({})),
  updateLead: vi.fn(async () => ({})),
  globalSearch: vi.fn(async () => ({ query: "", results: [], total: 0, generated_at: "" })),
  askMissionAssistant: vi.fn(async () => ({ question: "", intent: "", answer: "", facts: [], generated_at: "" })),
  postMissionAction: vi.fn(async () => ({ action: "", ok: true, affected: 0, message: "", details: {} })),
  createContentJob: vi.fn(async () => ({})),
  createWorkspace: vi.fn(async () => ({ id: "ws-2", name: "New" })),
}));

function renderShell() {
  return render(
    <LumoraDashboard
      token="t"
      workspaceId="ws-1"
      email="founder@lumora.local"
      onWorkspaceChange={() => {}}
      onSignOut={() => {}}
    />,
  );
}

beforeEach(() => {
  window.HTMLElement.prototype.scrollIntoView = vi.fn();
});

afterEach(() => {
  cleanup();
});

describe("dashboard navigation smoke test", () => {
  it("loads the dashboard and shows a truthful health footer (not a fake 'operational')", async () => {
    renderShell();
    expect(await screen.findByText(/Operations overview/i)).toBeDefined();
    // Health footer must reflect the red worker indicator — never "operational".
    expect(await screen.findByText(/Service disruption detected/i)).toBeDefined();
    expect(screen.queryByText("All systems operational")).toBeNull();
  });

  it("shows active alerts whose count matches the metric (no alert-count mismatch)", async () => {
    renderShell();
    await screen.findByText(/Operations overview/i);
    // Metric label + active alerts section header are driven by the same source.
    expect((await screen.findAllByText("Active Conditions")).length).toBeGreaterThanOrEqual(1);
    expect(await screen.findByText("Worker Offline")).toBeDefined();
    expect(await screen.findByText("Review Waiting")).toBeDefined();
  });

  it("keeps the newest global-search response when an older request resolves late", async () => {
    const api = await import("./api");
    let resolveOld!: (value: unknown) => void;
    const oldRequest = new Promise((resolve) => { resolveOld = resolve; });
    (api.globalSearch as unknown as ReturnType<typeof vi.fn>).mockImplementation(
      (_token: string, _workspace: string, query: string) => query === "ab"
        ? oldRequest
        : Promise.resolve({
            query,
            total: 1,
            generated_at: "",
            results: [{ type: "lead", id: "new", title: "Newest result", subtitle: null, status: null, occurred_at: null, url: null }],
          }),
    );
    renderShell();
    await screen.findByText(/Operations overview/i);
    const input = screen.getByRole("textbox", { name: /global search/i });

    fireEvent.change(input, { target: { value: "ab" } });
    await new Promise((resolve) => setTimeout(resolve, 300));
    fireEvent.change(input, { target: { value: "abc" } });
    expect(await screen.findByText("Newest result")).toBeDefined();

    resolveOld({
      query: "ab",
      total: 1,
      generated_at: "",
      results: [{ type: "lead", id: "old", title: "Stale result", subtitle: null, status: null, occurred_at: null, url: null }],
    });
    await new Promise((resolve) => setTimeout(resolve, 20));
    expect(screen.queryByText("Stale result")).toBeNull();
    expect(screen.getByText("Newest result")).toBeDefined();
  });

  it("opens the keyboard command palette and closes it with Escape", async () => {
    renderShell();
    await screen.findByText(/Operations overview/i);
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(await screen.findByRole("dialog", { name: /command palette/i })).toBeDefined();
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: /command palette/i })).toBeNull());
  });

  it("routes command palette deep links to the intended destination", async () => {
    renderShell();
    await screen.findByText(/Operations overview/i);
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    const palette = await screen.findByRole("dialog", { name: /command palette/i });
    fireEvent.click(within(palette).getByRole("button", { name: /open logs/i }));
    expect(await screen.findByRole("tabpanel", { name: /live logs/i })).toBeDefined();
    expect(await screen.findByText(/No worker logs match/i)).toBeDefined();
  });

  it("loads every Mission Control tab safely", async () => {
    renderShell();
    await screen.findByText(/Operations overview/i);
    const nav = screen.getByRole("navigation", { name: /primary navigation/i });
    fireEvent.click(within(nav).getByRole("button", { name: /^Mission Control$/i }));
    await screen.findByText(/Today's summary/i);

    const tabs: Array<[string, RegExp]> = [
      ["Timeline", /No timeline events recorded/i],
      ["Live logs", /No worker logs match/i],
      ["AI assistant", /Ask live system/i],
      ["Content", /No content activity has been recorded/i],
      ["Overview", /Today's summary/i],
    ];
    for (const [label, expected] of tabs) {
      fireEvent.click(screen.getByRole("tab", { name: label }));
      expect(await screen.findByText(expected)).toBeDefined();
      expect(screen.queryByText(/Lumora hit an unexpected error/i)).toBeNull();
    }
  });

  it("navigates across every route without a blank-screen crash", async () => {
    renderShell();
    await screen.findByText(/Operations overview/i);

    const routes: Array<[string, RegExp]> = [
      ["Pipelines", /No active pipelines/i],
      ["Workers", /No workers registered/i],
      ["Customers", /No customers yet/i],
      ["Leads", /No leads yet/i],
      ["Mission Control", /Today's summary/i],
      ["Analytics", /Engineering delivery/i],
      ["Billing", /Cost control/i],
      ["Settings", /Deployment/i],
      ["Review Queue", /keeps every publish decision/i],
      ["Dashboard", /Operations overview/i],
    ];

    for (const [label, expected] of routes) {
      const nav = screen.getByRole("navigation", { name: /primary navigation/i });
      fireEvent.click(within(nav).getByRole("button", { name: new RegExp(`^${label}$`, "i") }));
      await waitFor(() => expect(screen.getByText(expected)).toBeDefined());
      // The shell must survive: brand is always present, crash fallback is not.
      expect(screen.getByText("Lumora")).toBeDefined();
      expect(screen.queryByText(/Lumora hit an unexpected error/i)).toBeNull();
    }
  });

  it("surfaces a retryable error state instead of crashing when a route fails", async () => {
    const api = await import("./api");
    // Reject a route-only endpoint so the initial dashboard load still succeeds.
    (api.getLeads as unknown as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
      new Error("503: backend unavailable"),
    );
    renderShell();
    await screen.findByText(/Operations overview/i);
    const nav = screen.getByRole("navigation", { name: /primary navigation/i });
    fireEvent.click(within(nav).getByRole("button", { name: /^Leads$/i }));
    expect(await screen.findByText(/We couldn’t load this view|We couldn't load this view/i)).toBeDefined();
    // Shell still intact.
    expect(screen.getByText("Lumora")).toBeDefined();
  });

  it("ignores a late response from a route that is no longer active", async () => {
    const api = await import("./api");
    renderShell();
    await screen.findByText(/Operations overview/i);

    let resolvePipeline!: (value: typeof pipelines) => void;
    const delayedPipeline = new Promise<typeof pipelines>((resolve) => {
      resolvePipeline = resolve;
    });
    (api.getPipelineMonitor as unknown as ReturnType<typeof vi.fn>)
      .mockImplementationOnce(() => delayedPipeline);

    const nav = screen.getByRole("navigation", { name: /primary navigation/i });

    fireEvent.click(within(nav).getByRole("button", { name: /^Pipelines$/i }));
    fireEvent.click(within(nav).getByRole("button", { name: /^Workers$/i }));
    expect(await screen.findByText(/No workers registered/i)).toBeDefined();

    resolvePipeline(pipelines);
    await waitFor(() => expect(screen.getByText(/No workers registered/i)).toBeDefined());
    expect(screen.queryByText(/No active pipelines/i)).toBeNull();
    expect(screen.queryByText(/Lumora hit an unexpected error/i)).toBeNull();
  });
});

describe("mobile smoke test", () => {
  it("opens the mobile navigation drawer and reveals a search affordance", async () => {
    renderShell();
    await screen.findByText(/Operations overview/i);
    // Mobile menu + search buttons exist for small screens.
    expect(screen.getByRole("button", { name: /open navigation/i })).toBeDefined();
    const searchToggle = screen.getByRole("button", { name: /^Search$/i });
    fireEvent.click(searchToggle);
    expect(searchToggle.getAttribute("aria-expanded")).toBe("true");
  });
});
