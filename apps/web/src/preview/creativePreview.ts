/**
 * Disposable visual-preview adapter.
 *
 * Enabled only when the web build sets VITE_CREATIVE_PREVIEW=1 (Vercel
 * preview builds). Production Docker/local AUTH_MODE=local builds leave
 * this unset, so fetch still goes to the real API.
 *
 * This adapter never publishes, never spends provider money, and never
 * claims a live workspace. Review decisions stay in memory for this tab.
 */

const GENERATED_AT = "2026-09-04T18:00:00Z";

export function isCreativePreview(): boolean {
  return import.meta.env.VITE_CREATIVE_PREVIEW === "1";
}

type Gate = {
  id: string;
  workspace_id: string;
  pipeline_run_id: string;
  content_item_id: string;
  topic: string;
  stage: string;
  status: string;
  requested_at: string;
  timeout_at: string | null;
  decided_at: string | null;
  decided_by: string | null;
  script_hook: string | null;
  script_body: string | null;
  script_cta: string | null;
  run_status: string;
};

const previewGates: Gate[] = [
  {
    id: "preview-gate-1",
    workspace_id: "preview-ws",
    pipeline_run_id: "preview-pipe-1001",
    content_item_id: "preview-item-1",
    topic: "PREVIEW DATA — Founder script awaiting Human Review",
    stage: "human_review",
    status: "awaiting",
    requested_at: GENERATED_AT,
    timeout_at: null,
    decided_at: null,
    decided_by: null,
    script_hook: "Open with the decision that is waiting.",
    script_body: "This is labeled preview content. Approve/Reject only updates this browser tab.",
    script_cta: "Human Review Gate still blocks external publish.",
    run_status: "waiting_review",
  },
];

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "content-type": "application/json" },
  });
}

function operations(pathname: string, method: string, body: unknown): unknown {
  if (pathname.endsWith("/operations/executive")) {
    return {
      workers_online: 0,
      workers_busy: 0,
      jobs_running: 1,
      jobs_queued: 0,
      jobs_failed: 1,
      human_reviews_waiting: previewGates.filter((gate) => gate.status === "awaiting").length,
      spend_today_usd: "4.20",
      spend_month_usd: "18.75",
      active_workspaces: 1,
      deployment: {
        ci_status: "success",
        ci_url: null,
        git_branch: "cursor/human-creative-workspace-fc76",
        commit_sha: "previewsha",
        deployed_at: GENERATED_AT,
      },
      generated_at: GENERATED_AT,
    };
  }
  if (pathname.endsWith("/operations/pipelines")) {
    return {
      active_pipelines: 0,
      queue_depth: 0,
      failed_pipelines: 0,
      retrying_pipelines: 0,
      dead_letter_queue: 0,
      review_gates: previewGates.length,
      publish_queue: 0,
      jobs_completed: 3,
      jobs_waiting: 0,
      jobs_failed: 0,
      human_reviews_waiting: previewGates.filter((gate) => gate.status === "awaiting").length,
      publishing_queue: 0,
      pipelines: [],
      generated_at: GENERATED_AT,
    };
  }
  if (pathname.endsWith("/operations/alerts") || pathname.endsWith("/operations/notifications")) {
    return {
      alerts: [
        { key: "a1", severity: "critical", title: "Worker Offline", count: 2, message: "PREVIEW DATA — 2 workers offline" },
        { key: "a2", severity: "warning", title: "Review Waiting", count: previewGates.filter((gate) => gate.status === "awaiting").length, message: "PREVIEW DATA — Human Review items waiting" },
      ],
      notifications: [
        { key: "a2", severity: "warning", title: "Review Waiting", message: "PREVIEW DATA — Human Review items waiting" },
      ],
      generated_at: GENERATED_AT,
    };
  }
  if (pathname.endsWith("/operations/health")) {
    return {
      indicators: [
        { key: "api", label: "API Health", status: "green", detail: "visual preview adapter" },
        { key: "worker", label: "Worker Health", status: "red", detail: "0/2 workers live" },
      ],
      generated_at: GENERATED_AT,
    };
  }
  if (pathname.endsWith("/operations/customers")) {
    return {
      beta_users: 0,
      active_users: 0,
      paying_users: 0,
      trial_users: 0,
      revenue_mtd_usd: "0",
      revenue_source: "stripe",
      customers: [],
      generated_at: GENERATED_AT,
    };
  }
  if (pathname.endsWith("/operations/executive-mode")) {
    return {
      health: [
        { key: "api", label: "API Health", status: "green", detail: "visual preview adapter" },
        { key: "worker", label: "Worker Health", status: "red", detail: "0/2 workers live" },
      ],
      revenue_mtd_usd: "0",
      spend_today_usd: "4.20",
      spend_month_usd: "18.75",
      workers_online: 0,
      workers_total: 2,
      jobs_running: 1,
      jobs_waiting: 0,
      jobs_failed_today: 1,
      critical_alerts: 1,
      reviews_waiting: previewGates.filter((gate) => gate.status === "awaiting").length,
      new_customers_today: 0,
      todays_summary: ["Disposable visual preview. External publishing remains disabled."],
      generated_at: GENERATED_AT,
    };
  }
  if (pathname.endsWith("/operations/spend")) {
    return {
      today_usd: "4.20",
      week_usd: "11.00",
      month_usd: "18.75",
      by_provider: [],
      daily_cap_usd: "25.00",
      monthly_cap_usd: "100.00",
      budget_remaining_daily_usd: "20.80",
      budget_remaining_monthly_usd: "81.25",
      generated_at: GENERATED_AT,
    };
  }
  if (pathname.endsWith("/operations/cost-control")) {
    return {
      daily_ai_spend_usd: "4.20",
      monthly_ai_spend_usd: "18.75",
      budget_remaining_daily_usd: "20.80",
      budget_remaining_monthly_usd: "81.25",
      by_provider: [],
      top_expensive_jobs: [],
      projected_month_end_usd: "37.50",
      generated_at: GENERATED_AT,
    };
  }
  if (pathname.endsWith("/operations/activity") || pathname.endsWith("/operations/timeline")) {
    return { items: [], generated_at: GENERATED_AT };
  }
  if (pathname.endsWith("/operations/logs")) {
    return { logs: [], generated_at: GENERATED_AT };
  }
  if (pathname.endsWith("/operations/content-command")) {
    return {
      ideas: 0, scripts: 0, voiceovers: 0, videos_rendering: 0, ready_for_review: 0,
      waiting_for_approval: 0, publishing: 0, published: 0, failed: 0, generated_at: GENERATED_AT,
    };
  }
  if (pathname.endsWith("/operations/workers") || pathname.endsWith("/operations/worker-timeline")) {
    return { workers: [], generated_at: GENERATED_AT };
  }
  if (pathname.endsWith("/operations/leads")) {
    return { leads: [], total: 0, generated_at: GENERATED_AT };
  }
  if (pathname.endsWith("/operations/insights")) {
    return {
      todays_achievements: [],
      todays_failures: [],
      highest_risk: "None",
      suggested_next_action: "Review the visual theme, then return to a live workspace for real work.",
      biggest_cost_today_usd: "4.20",
      biggest_cost_today_label: "preview fixture",
      most_active_worker: null,
      most_active_customer: null,
      generated_at: GENERATED_AT,
    };
  }
  if (pathname.endsWith("/operations/github")) {
    return {
      available: false,
      unavailable_reason: "GitHub is not connected in this visual preview.",
      repository: null,
      latest_commits: [],
      open_pull_requests: [],
      failed_actions: [],
      branch_status: { name: null, sha: null, protected: null, ci_status: "unknown" },
      generated_at: GENERATED_AT,
    };
  }
  if (pathname.endsWith("/operations/search")) {
    return { query: "", results: [], total: 0, generated_at: GENERATED_AT };
  }
  if (pathname.includes("/operations/actions/") && method === "POST") {
    return {
      action: "preview",
      ok: false,
      affected: 0,
      message: "Preview adapter refused the operator action. No live workers or queues were changed.",
      details: {},
    };
  }
  if (pathname.endsWith("/research/summary")) {
    return {
      provider_state: "not_configured",
      status: "not_run",
      current_research: null,
      last_run: null,
      next_run_at: null,
      opportunities_found: 0,
      audited_opportunities: 0,
      blocked_findings: 0,
      cost_today_usd: "0",
      last_error: "RESEARCH PROVIDER NOT CONFIGURED",
      schedule_enabled: false,
      research_data_state: "not_connected",
    };
  }
  if (pathname.endsWith("/research/opportunities") || pathname.endsWith("/strategy/briefs") || pathname.endsWith("/content-department/packages") || pathname.endsWith("/production/runs")) {
    return [];
  }
  if (pathname.endsWith("/strategy/summary")) {
    return {
      provider_state: "not_configured",
      status: "not_run",
      current_strategy: null,
      last_run: null,
      briefs_ready: 0,
      audited_briefs: 0,
      blocked_findings: 0,
      cost_today_usd: "0",
      last_error: "STRATEGY PROVIDER NOT CONFIGURED",
    };
  }
  if (pathname.endsWith("/content-department/summary")) {
    return { provider_state: "not_configured", packages: 0, audited: 0, blocked: 0, cost_today_usd: "0" };
  }
  if (pathname.endsWith("/production/summary")) {
    return {
      provider_state: "not_configured",
      final_artifacts: 0,
      media_qa_passed: 0,
      media_qa_blocked: 0,
      repair_required: 0,
      provider_cost_usd: "0",
    };
  }
  if (pathname.endsWith("/compliance/summary")) {
    return { provider_state: "not_configured", audits: 0, blocked: 0, ready_for_human_review: previewGates.filter((gate) => gate.status === "awaiting").length };
  }
  if (pathname.endsWith("/compliance/audits") || pathname.endsWith("/compliance/chief-audits") || pathname.endsWith("/compliance/human-review-packages")) {
    return [];
  }
  if (pathname.includes("/review-gates/") && pathname.endsWith("/decision") && method === "POST") {
    const gateId = pathname.split("/review-gates/")[1]?.split("/")[0];
    const gate = previewGates.find((item) => item.id === gateId);
    if (!gate) return { detail: "Preview gate not found" };
    const approved = Boolean((body as { approved?: boolean } | null)?.approved);
    gate.status = approved ? "approved" : "rejected";
    gate.decided_at = new Date().toISOString();
    gate.decided_by = "preview-founder";
    return gate;
  }
  if (pathname.includes("/review-gates")) {
    const awaiting = previewGates.filter((gate) => gate.status === "awaiting");
    return awaiting;
  }
  return { generated_at: GENERATED_AT, preview: true };
}

export function installCreativePreviewFetch(): void {
  if (!isCreativePreview() || typeof window === "undefined") return;
  if (window.fetch.name === "creativePreviewFetch") return;

  const realFetch = window.fetch.bind(window);
  async function creativePreviewFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
    const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
    const parsed = new URL(url, window.location.origin);
    if (!parsed.pathname.startsWith("/api/")) {
      return realFetch(input, init);
    }

    const method = (init?.method ?? "GET").toUpperCase();
    let body: unknown = null;
    if (init?.body && typeof init.body === "string") {
      try {
        body = JSON.parse(init.body);
      } catch {
        body = null;
      }
    }

    if (parsed.pathname === "/api/auth/login" || parsed.pathname === "/api/auth/signup") {
      const email = typeof (body as { email?: string } | null)?.email === "string"
        ? (body as { email: string }).email
        : "preview@thebusinessmanager.local";
      return jsonResponse({
        access_token: "preview-visual-token",
        token_type: "bearer",
        expires_in: 3600,
        user_id: "preview-user",
        email,
      });
    }
    if (parsed.pathname === "/api/workspaces" && method === "GET") {
      return jsonResponse([{ id: "preview-ws", name: "Preview Workspace" }]);
    }
    if (parsed.pathname === "/api/workspaces" && method === "POST") {
      return jsonResponse({ id: "preview-ws", name: "Preview Workspace" });
    }
    if (parsed.pathname === "/api/auth/mode") {
      return jsonResponse({ auth_mode: "preview" });
    }

    return jsonResponse(operations(parsed.pathname, method, body));
  }

  window.fetch = creativePreviewFetch;
}
