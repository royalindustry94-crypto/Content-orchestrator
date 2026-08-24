export type ContentJob = {
  content_item_id: string;
  pipeline_run_id: string;
  review_gate_id: string;
  topic: string;
  current_stage: string;
  run_status: string;
  gate_status: string;
};

export type ReviewGate = {
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

export type AuthToken = {
  access_token: string;
  token_type: string;
  expires_in: number;
  user_id: string;
  email: string;
};

export type Workspace = {
  id: string;
  name: string;
};

export type DeploymentInfo = {
  ci_status: string;
  ci_url: string | null;
  git_branch: string | null;
  commit_sha: string | null;
  deployed_at: string | null;
};

export type ExecutiveDashboard = {
  workers_online: number;
  workers_busy: number;
  jobs_running: number;
  jobs_queued: number;
  jobs_failed: number;
  human_reviews_waiting: number;
  spend_today_usd: string;
  spend_month_usd: string;
  active_workspaces: number;
  deployment: DeploymentInfo;
  generated_at: string;
};

export type WorkerMonitorRow = {
  id: string;
  name: string;
  status: string;
  current_job: string | null;
  current_task: string | null;
  queue: number;
  last_heartbeat_at: string | null;
  retry_count: number;
  jobs_completed: number;
  jobs_failed: number;
  jobs_completed_today: number;
  jobs_failed_today: number;
  cpu_percent: number | null;
  memory_percent: number | null;
  lease_status: string;
};

export type WorkerMonitor = {
  workers: WorkerMonitorRow[];
  generated_at: string;
};

export type PipelineRow = {
  id: string;
  status: string;
  current_stage: string;
  pause_reason: string | null;
  created_at: string;
  updated_at: string;
};

export type PipelineMonitor = {
  active_pipelines: number;
  queue_depth: number;
  failed_pipelines: number;
  retrying_pipelines: number;
  dead_letter_queue: number;
  review_gates: number;
  publish_queue: number;
  jobs_completed: number;
  jobs_waiting: number;
  jobs_failed: number;
  human_reviews_waiting: number;
  publishing_queue: number;
  pipelines: PipelineRow[];
  generated_at: string;
};

export type OperationsAlert = {
  key: string;
  severity: "critical" | "warning" | "info";
  title: string;
  count: number;
  message: string;
  occurred_at?: string | null;
};

export type Alerts = {
  alerts: OperationsAlert[];
  generated_at: string;
};

export type Notifications = {
  notifications: OperationsAlert[];
  generated_at: string;
};

export type Lead = {
  id: string;
  workspace_id: string;
  name: string;
  company: string | null;
  email: string;
  source: string;
  status: string;
  notes: string | null;
  follow_up_date: string | null;
  created_at: string;
  updated_at: string;
};

export type Leads = {
  leads: Lead[];
  total: number;
  generated_at: string;
};

export type LeadInput = {
  name: string;
  company?: string | null;
  email: string;
  source?: string;
  status?: string;
  notes?: string | null;
  follow_up_date?: string | null;
};

export type CustomerRow = {
  workspace_id: string;
  name: string;
  plan: string;
  subscription_status: string;
  member_count: number;
  stripe_customer_id: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
  created_at: string;
};

export type Customers = {
  beta_users: number;
  active_users: number;
  paying_users: number;
  trial_users: number;
  revenue_mtd_usd: string;
  revenue_source: string;
  customers: CustomerRow[];
  generated_at: string;
};

export type SpendProviderRow = {
  provider: string;
  today_usd: string;
  week_usd: string;
  month_usd: string;
};

export type SpendDashboard = {
  today_usd: string;
  week_usd: string;
  month_usd: string;
  by_provider: SpendProviderRow[];
  daily_cap_usd: string | null;
  monthly_cap_usd: string | null;
  budget_remaining_daily_usd: string | null;
  budget_remaining_monthly_usd: string | null;
  generated_at: string;
};

export type GitHubOut = {
  available: boolean;
  unavailable_reason: string | null;
  repository: string | null;
  latest_commits: Array<{
    sha: string;
    message: string;
    author: string | null;
    committed_at: string | null;
    url: string | null;
  }>;
  open_pull_requests: Array<{
    number: number;
    title: string;
    state: string;
    author: string | null;
    updated_at: string | null;
    url: string | null;
    merged_at?: string | null;
  }>;
  recently_merged_pull_requests?: Array<{
    number: number;
    title: string;
    state: string;
    author: string | null;
    updated_at: string | null;
    url: string | null;
    merged_at?: string | null;
  }>;
  failed_actions: Array<{
    id: number;
    name: string;
    status: string;
    conclusion: string | null;
    branch: string | null;
    updated_at: string | null;
    url: string | null;
  }>;
  branch_status: {
    name: string | null;
    sha: string | null;
    protected: boolean | null;
    ci_status: string;
  };
  generated_at: string;
};

export type ActivityFeed = {
  items: Array<{
    id: string;
    kind: string;
    title: string;
    detail: string | null;
    severity: string;
    occurred_at: string;
    source: string;
  }>;
  generated_at: string;
};

export type SystemHealth = {
  indicators: Array<{
    key: string;
    label: string;
    status: string;
    detail: string;
  }>;
  generated_at: string;
};

export type CostControl = {
  daily_ai_spend_usd: string;
  monthly_ai_spend_usd: string;
  budget_remaining_daily_usd: string | null;
  budget_remaining_monthly_usd: string | null;
  by_provider: Array<{ provider: string; today_usd: string; month_usd: string }>;
  top_expensive_jobs: Array<{
    pipeline_run_id: string | null;
    content_item_id: string | null;
    topic: string | null;
    stage: string | null;
    provider: string | null;
    cost_usd: string;
    completed_at: string | null;
  }>;
  projected_month_end_usd: string;
  generated_at: string;
};

export type WorkerTimeline = {
  workers: Array<{
    worker_id: string;
    name: string;
    status: string;
    current_task: string | null;
    last_heartbeat_at: string | null;
    average_execution_seconds: number | null;
    failure_percent: number;
    retry_percent: number;
    jobs: Array<{
      assignment_id: string;
      pipeline_run_id: string;
      stage: string;
      status: string;
      attempt_number: number;
      dispatched_at: string | null;
      completed_at: string | null;
      duration_seconds: number | null;
    }>;
  }>;
  generated_at: string;
};

export type ContentCommand = {
  ideas: number;
  scripts: number;
  voiceovers: number;
  videos_rendering: number;
  ready_for_review: number;
  waiting_for_approval: number;
  publishing: number;
  published: number;
  failed: number;
  generated_at: string;
};

export type ExecutiveInsights = {
  todays_achievements: string[];
  todays_failures: string[];
  highest_risk: string;
  suggested_next_action: string;
  biggest_cost_today_usd: string;
  biggest_cost_today_label: string | null;
  most_active_worker: string | null;
  most_active_customer: string | null;
  generated_at: string;
};

export type QuickActionResult = {
  action: string;
  ok: boolean;
  affected: number;
  message: string;
  details: Record<string, unknown>;
};

export type SearchResult = {
  type: string;
  id: string;
  title: string;
  subtitle: string | null;
  status: string | null;
  occurred_at: string | null;
  url: string | null;
};

export type GlobalSearch = {
  query: string;
  results: SearchResult[];
  total: number;
  generated_at: string;
};

export type LiveLogs = {
  logs: Array<{
    id: string;
    workspace_id: string;
    worker_id: string;
    worker_name: string;
    pipeline_run_id: string | null;
    assignment_id: string | null;
    severity: string;
    message: string;
    context: Record<string, unknown>;
    occurred_at: string;
    received_at: string;
  }>;
  generated_at: string;
};

export type ExecutiveMode = {
  health: SystemHealth["indicators"];
  revenue_mtd_usd: string;
  spend_today_usd: string;
  spend_month_usd: string;
  workers_online: number;
  workers_total: number;
  jobs_running: number;
  jobs_waiting: number;
  jobs_failed_today: number;
  critical_alerts: number;
  reviews_waiting: number;
  new_customers_today: number;
  todays_summary: string[];
  generated_at: string;
};

export type AssistantAnswer = {
  question: string;
  intent: string;
  answer: string;
  facts: Array<Record<string, unknown>>;
  generated_at: string;
};

async function apiFetch<T>(
  path: string,
  token: string | null,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  if (init.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`/api${path}`, { ...init, headers });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status}: ${detail || response.statusText}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function getAuthMode(): Promise<{ auth_mode: string }> {
  return apiFetch<{ auth_mode: string }>("/auth/mode", null);
}

export function signup(
  email: string,
  password: string,
  fullName?: string,
): Promise<AuthToken> {
  return apiFetch<AuthToken>("/auth/signup", null, {
    method: "POST",
    body: JSON.stringify({
      email,
      password,
      full_name: fullName,
    }),
  });
}

export function login(email: string, password: string): Promise<AuthToken> {
  return apiFetch<AuthToken>("/auth/login", null, {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function createWorkspace(token: string, name: string): Promise<Workspace> {
  return apiFetch<Workspace>("/workspaces", token, {
    method: "POST",
    body: JSON.stringify({ name }),
  });
}

export function listWorkspaces(token: string): Promise<Workspace[]> {
  return apiFetch<Workspace[]>("/workspaces", token);
}

export function getExecutiveDashboard(
  token: string,
  workspaceId: string,
): Promise<ExecutiveDashboard> {
  return apiFetch<ExecutiveDashboard>(
    `/workspaces/${workspaceId}/operations/executive`,
    token,
  );
}

export function getWorkerMonitor(
  token: string,
  workspaceId: string,
): Promise<WorkerMonitor> {
  return apiFetch<WorkerMonitor>(
    `/workspaces/${workspaceId}/operations/workers`,
    token,
  );
}

export function getPipelineMonitor(
  token: string,
  workspaceId: string,
): Promise<PipelineMonitor> {
  return apiFetch<PipelineMonitor>(
    `/workspaces/${workspaceId}/operations/pipelines`,
    token,
  );
}

export function getOperationsAlerts(
  token: string,
  workspaceId: string,
): Promise<Alerts> {
  return apiFetch<Alerts>(
    `/workspaces/${workspaceId}/operations/alerts`,
    token,
  );
}

export function getNotifications(
  token: string,
  workspaceId: string,
): Promise<Notifications> {
  return apiFetch<Notifications>(
    `/workspaces/${workspaceId}/operations/notifications`,
    token,
  );
}

export function getLeads(
  token: string,
  workspaceId: string,
  params: { search?: string; status?: string; source?: string } = {},
): Promise<Leads> {
  const query = new URLSearchParams();
  if (params.search) query.set("search", params.search);
  if (params.status) query.set("status", params.status);
  if (params.source) query.set("source", params.source);
  const suffix = query.toString() ? `?${query}` : "";
  return apiFetch<Leads>(
    `/workspaces/${workspaceId}/operations/leads${suffix}`,
    token,
  );
}

export function createLead(
  token: string,
  workspaceId: string,
  payload: LeadInput,
): Promise<Lead> {
  return apiFetch<Lead>(`/workspaces/${workspaceId}/operations/leads`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateLead(
  token: string,
  workspaceId: string,
  leadId: string,
  payload: Partial<LeadInput>,
): Promise<Lead> {
  return apiFetch<Lead>(
    `/workspaces/${workspaceId}/operations/leads/${leadId}`,
    token,
    {
      method: "PATCH",
      body: JSON.stringify(payload),
    },
  );
}

export function getCustomers(
  token: string,
  workspaceId: string,
): Promise<Customers> {
  return apiFetch<Customers>(
    `/workspaces/${workspaceId}/operations/customers`,
    token,
  );
}

export function getSpendDashboard(
  token: string,
  workspaceId: string,
): Promise<SpendDashboard> {
  return apiFetch<SpendDashboard>(
    `/workspaces/${workspaceId}/operations/spend`,
    token,
  );
}

export function getGitHubStatus(
  token: string,
  workspaceId: string,
): Promise<GitHubOut> {
  return apiFetch<GitHubOut>(
    `/workspaces/${workspaceId}/operations/github`,
    token,
  );
}

export function getActivityFeed(
  token: string,
  workspaceId: string,
): Promise<ActivityFeed> {
  return apiFetch<ActivityFeed>(
    `/workspaces/${workspaceId}/operations/activity`,
    token,
  );
}

export function getSystemHealth(
  token: string,
  workspaceId: string,
): Promise<SystemHealth> {
  return apiFetch<SystemHealth>(
    `/workspaces/${workspaceId}/operations/health`,
    token,
  );
}

export function getCostControl(
  token: string,
  workspaceId: string,
): Promise<CostControl> {
  return apiFetch<CostControl>(
    `/workspaces/${workspaceId}/operations/cost-control`,
    token,
  );
}

export function getWorkerTimeline(
  token: string,
  workspaceId: string,
): Promise<WorkerTimeline> {
  return apiFetch<WorkerTimeline>(
    `/workspaces/${workspaceId}/operations/worker-timeline`,
    token,
  );
}

export function getContentCommand(
  token: string,
  workspaceId: string,
): Promise<ContentCommand> {
  return apiFetch<ContentCommand>(
    `/workspaces/${workspaceId}/operations/content-command`,
    token,
  );
}

export function getExecutiveInsights(
  token: string,
  workspaceId: string,
): Promise<ExecutiveInsights> {
  return apiFetch<ExecutiveInsights>(
    `/workspaces/${workspaceId}/operations/insights`,
    token,
  );
}

export function globalSearch(
  token: string,
  workspaceId: string,
  query: string,
): Promise<GlobalSearch> {
  return apiFetch<GlobalSearch>(
    `/workspaces/${workspaceId}/operations/search?q=${encodeURIComponent(query)}`,
    token,
  );
}

export function getUniversalTimeline(
  token: string,
  workspaceId: string,
): Promise<ActivityFeed> {
  return apiFetch<ActivityFeed>(
    `/workspaces/${workspaceId}/operations/timeline`,
    token,
  );
}

export function getLiveLogs(
  token: string,
  workspaceId: string,
  filters: {
    worker_id?: string;
    pipeline_id?: string;
    job_id?: string;
    severity?: string;
  } = {},
): Promise<LiveLogs> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const suffix = params.toString() ? `?${params}` : "";
  return apiFetch<LiveLogs>(
    `/workspaces/${workspaceId}/operations/logs${suffix}`,
    token,
  );
}

export function getExecutiveMode(
  token: string,
  workspaceId: string,
): Promise<ExecutiveMode> {
  return apiFetch<ExecutiveMode>(
    `/workspaces/${workspaceId}/operations/executive-mode`,
    token,
  );
}

export function askMissionAssistant(
  token: string,
  workspaceId: string,
  question: string,
): Promise<AssistantAnswer> {
  return apiFetch<AssistantAnswer>(
    `/workspaces/${workspaceId}/operations/assistant`,
    token,
    { method: "POST", body: JSON.stringify({ question }) },
  );
}

export function postMissionAction(
  token: string,
  workspaceId: string,
  action:
    | "pause-workers"
    | "resume-workers"
    | "emergency-stop"
    | "retry-failed-jobs"
    | "clear-dead-letter"
    | "sync-github",
): Promise<QuickActionResult> {
  return apiFetch<QuickActionResult>(
    `/workspaces/${workspaceId}/operations/actions/${action}`,
    token,
    { method: "POST" },
  );
}

export function createContentJob(
  token: string,
  workspaceId: string,
  payload: {
    topic: string;
    script_body?: string;
    script_hook?: string;
    script_cta?: string;
  },
): Promise<ContentJob> {
  return apiFetch<ContentJob>(`/workspaces/${workspaceId}/content-jobs`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listReviewGates(
  token: string,
  workspaceId: string,
  status = "awaiting",
): Promise<ReviewGate[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  return apiFetch<ReviewGate[]>(
    `/workspaces/${workspaceId}/review-gates${query}`,
    token,
  );
}

export function decideReviewGate(
  token: string,
  workspaceId: string,
  gateId: string,
  approved: boolean,
  notes?: string,
): Promise<ReviewGate> {
  return apiFetch<ReviewGate>(
    `/workspaces/${workspaceId}/review-gates/${gateId}/decision`,
    token,
    {
      method: "POST",
      body: JSON.stringify({ approved, notes }),
    },
  );
}

export type ResearchRun = {
  id: string;
  workspace_id: string;
  trigger: string;
  research_objective: string;
  permitted_sources: string[];
  started_at: string;
  deadline: string;
  max_searches: number;
  max_provider_calls: number;
  max_tokens: number;
  max_cost_usd: string;
  max_attempts: number;
  status: string;
  provider_state: string;
  searches_used: number;
  provider_calls_used: number;
  tokens_used: number;
  reserved_cost_usd: string;
  actual_cost_usd: string;
  opportunity_count: number;
  audited_opportunity_count: number;
  blocked_opportunity_count: number;
  last_error: string | null;
  correlation_id: string;
  trace_id: string | null;
  test_data: boolean;
};

export type ResearchSource = {
  id: string;
  research_run_id: string;
  canonical_url: string;
  source_type: string;
  retrieved_at: string;
  published_at: string | null;
  publisher: string | null;
  author: string | null;
  claim_supported: string | null;
  freshness: string;
  confidence: string;
  handling_state: string;
  rejection_reason: string | null;
  test_data: boolean;
};

export type Opportunity = {
  id: string;
  research_run_id: string;
  title: string;
  topic: string;
  summary: string;
  proposed_angle: string;
  target_audience: string | null;
  target_platform: string | null;
  suggested_format: string | null;
  discovered_at: string;
  freshness: string;
  source_count: number;
  confidence: string;
  risk: string;
  status: string;
  created_by_worker: string;
  component_scores: Record<string, number>;
  score_reasoning: Record<string, string>;
  audit_gate_status: string;
  performance_data_state: string;
  strategist_state: string;
  test_data: boolean;
};

export type OpportunityEvidence = {
  source: ResearchSource;
  claim_supported: string;
  relevance: string;
  contradiction_flag: boolean;
};

export type ResearchAudit = {
  id: string;
  opportunity_id: string;
  research_run_id: string;
  state: string;
  evaluator_context_version: string;
  findings: Array<Record<string, string>>;
  warnings: string[];
  blocked_reasons: string[];
  checked_at: string;
  test_data: boolean;
};

export type OpportunityDetail = {
  opportunity: Opportunity;
  evidence: OpportunityEvidence[];
  latest_audit: ResearchAudit | null;
};

export type ResearchSummary = {
  provider_state: string;
  status: string;
  current_research: ResearchRun | null;
  last_run: ResearchRun | null;
  next_run_at: string | null;
  opportunities_found: number;
  audited_opportunities: number;
  blocked_findings: number;
  cost_today_usd: string;
  last_error: string | null;
  schedule_enabled: boolean;
  research_data_state: string;
};

export type StrategistGate = {
  opportunity_id: string;
  eligible: boolean;
  state: string;
  detail: string;
};

export function getResearchSummary(token: string, workspaceId: string): Promise<ResearchSummary> {
  return apiFetch<ResearchSummary>(`/workspaces/${workspaceId}/research/summary`, token);
}

export function listResearchRuns(token: string, workspaceId: string): Promise<ResearchRun[]> {
  return apiFetch<ResearchRun[]>(`/workspaces/${workspaceId}/research/runs`, token);
}

export function createResearchRun(
  token: string,
  workspaceId: string,
  payload: {
    research_objective: string;
    permitted_sources?: string[];
    max_searches?: number;
    max_provider_calls?: number;
    max_tokens?: number;
    max_cost_usd?: string;
    max_attempts?: number;
  },
): Promise<ResearchRun> {
  return apiFetch<ResearchRun>(`/workspaces/${workspaceId}/research/runs`, token, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function listOpportunities(token: string, workspaceId: string): Promise<Opportunity[]> {
  return apiFetch<Opportunity[]>(`/workspaces/${workspaceId}/research/opportunities`, token);
}

export function getOpportunityDetail(
  token: string,
  workspaceId: string,
  opportunityId: string,
): Promise<OpportunityDetail> {
  return apiFetch<OpportunityDetail>(
    `/workspaces/${workspaceId}/research/opportunities/${opportunityId}`,
    token,
  );
}

export function auditOpportunity(
  token: string,
  workspaceId: string,
  opportunityId: string,
): Promise<ResearchAudit> {
  return apiFetch<ResearchAudit>(
    `/workspaces/${workspaceId}/research/opportunities/${opportunityId}/audit`,
    token,
    { method: "POST" },
  );
}

export function sendOpportunityToStrategist(
  token: string,
  workspaceId: string,
  opportunityId: string,
): Promise<StrategistGate> {
  return apiFetch<StrategistGate>(
    `/workspaces/${workspaceId}/research/opportunities/${opportunityId}/send-to-strategist`,
    token,
    { method: "POST" },
  );
}
