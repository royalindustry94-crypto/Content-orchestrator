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
  queue: number;
  last_heartbeat_at: string | null;
  retry_count: number;
  jobs_completed: number;
  jobs_failed: number;
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
  pipelines: PipelineRow[];
  generated_at: string;
};

export type OperationsAlert = {
  key: string;
  severity: "critical" | "warning" | "info";
  title: string;
  count: number;
  message: string;
};

export type Alerts = {
  alerts: OperationsAlert[];
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
