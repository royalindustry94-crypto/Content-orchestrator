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

async function apiFetch<T>(
  path: string,
  token: string,
  init: RequestInit = {},
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${token}`);
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

export function createContentJob(
  token: string,
  workspaceId: string,
  payload: {
    topic: string;
    script_body: string;
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
