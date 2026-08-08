// Verifies Human Review Gate behaviour, workspace isolation, and backend
// health against a running environment. It creates unique disposable tenants
// and decides only the gate it created; it never mutates seeded/customer data.
const BASE = process.env.API_BASE || "http://127.0.0.1:5173/api";
const runId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
const PASSWORD = process.env.SMOKE_PASSWORD || `${crypto.randomUUID()}Aa1!`;

const post = async (path, token, body) =>
  fetch(`${BASE}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });

const get = async (path, token) =>
  fetch(`${BASE}${path}`, { headers: { Authorization: `Bearer ${token}` } });

const results = [];
const record = (name, pass, detail) => {
  results.push({ name, pass, detail });
  console.log(`${pass ? "PASS" : "FAIL"} | ${name} | ${detail}`);
};

// Primary disposable tenant.
const signupPrimary = await post("/auth/signup", null, {
  email: `release-primary-${runId}@lumora.local`,
  password: PASSWORD,
});
const auth = await signupPrimary.json();
record("Primary tenant signup", signupPrimary.ok, `HTTP ${signupPrimary.status}`);
const token = auth.access_token;
const createWorkspace = await post("/workspaces", token, {
  name: `Release smoke ${runId}`,
});
const workspace = await createWorkspace.json();
record("Primary workspace creation", createWorkspace.ok, `HTTP ${createWorkspace.status}`);
const workspaceId = workspace.id;

// --- Human Review Gate ---
const createJob = await post(`/workspaces/${workspaceId}/content-jobs`, token, {
  topic: `Release gate smoke ${runId}`,
  script_body: "Release verification content",
});
record("HRG fixture content job", createJob.ok, `HTTP ${createJob.status}`);

const gates = await (await get(`/workspaces/${workspaceId}/review-gates?status=awaiting`, token)).json();
record("HRG list awaiting", Array.isArray(gates) && gates.length === 1, `${gates.length} gate(s) awaiting`);

if (gates.length > 0) {
  const gate = gates.find((item) => item.topic === `Release gate smoke ${runId}`) ?? gates[0];
  const decision = await post(
    `/workspaces/${workspaceId}/review-gates/${gate.id}/decision`,
    token,
    { approved: true, notes: "Post-audit HRG verification" },
  );
  const decided = await decision.json();
  record(
    "HRG approve decision persists",
    decision.ok && decided.status !== "awaiting" && decided.decided_at !== null,
    `status=${decided.status} decided_at=${decided.decided_at ? "set" : "null"}`,
  );

  const after = await (await get(`/workspaces/${workspaceId}/review-gates?status=awaiting`, token)).json();
  record(
    "HRG queue shrinks after decision",
    after.length === gates.length - 1,
    `${gates.length} -> ${after.length}`,
  );

  const reDecide = await post(
    `/workspaces/${workspaceId}/review-gates/${gate.id}/decision`,
    token,
    { approved: false },
  );
  record(
    "HRG rejects double-decision",
    !reDecide.ok,
    `HTTP ${reDecide.status} on second decision`,
  );
} else {
  record("HRG decision path", false, "no awaiting gate available to exercise");
}

// --- Workspace isolation ---
const otherEmail = `release-isolation-${runId}@lumora.local`;
const signup = await post("/auth/signup", null, { email: otherEmail, password: PASSWORD });
const other = await signup.json();
const otherToken = other.access_token;

const crossRead = await get(`/workspaces/${workspaceId}/operations/executive`, otherToken);
record(
  "Cross-tenant dashboard read denied",
  crossRead.status === 403 || crossRead.status === 404,
  `HTTP ${crossRead.status}`,
);

const crossGates = await get(`/workspaces/${workspaceId}/review-gates`, otherToken);
record(
  "Cross-tenant review gates denied",
  crossGates.status === 403 || crossGates.status === 404,
  `HTTP ${crossGates.status}`,
);

const crossHealth = await get(`/workspaces/${workspaceId}/operations/health`, otherToken);
record(
  "Cross-tenant health denied",
  crossHealth.status === 403 || crossHealth.status === 404,
  `HTTP ${crossHealth.status}`,
);

const anon = await fetch(`${BASE}/workspaces/${workspaceId}/operations/executive`);
record("Unauthenticated read denied", anon.status === 401 || anon.status === 403, `HTTP ${anon.status}`);

const otherWorkspaces = await (await get("/workspaces", otherToken)).json();
record(
  "New tenant cannot see foreign workspaces",
  !otherWorkspaces.some((w) => w.id === workspaceId),
  `${otherWorkspaces.length} workspace(s) visible`,
);

// --- Health truthfulness ---
const health = await (await get(`/workspaces/${workspaceId}/operations/health`, token)).json();
const hasLiveDetail = health.indicators.every((i) => typeof i.status === "string" && i.detail !== undefined);
record(
  "Health indicators sourced from backend",
  Array.isArray(health.indicators) && health.indicators.length > 0 && hasLiveDetail,
  `${health.indicators.length} indicators: ${health.indicators.map((i) => `${i.key}=${i.status}`).join(", ")}`,
);

const failed = results.filter((r) => !r.pass);
console.log(`\nTOTAL: ${results.length}  FAILED: ${failed.length}`);
process.exit(failed.length === 0 ? 0 : 1);
