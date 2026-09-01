/**
 * Isolated Founder Studio preview data layer.
 *
 * Lives only in the browser. Never talks to FastAPI, Supabase, or social APIs.
 * Persistence is sessionStorage so a refresh keeps the demo workflow without
 * pretending the backend accepted the fake preview token.
 */

export type PreviewPlatform = "tiktok" | "instagram" | "youtube";

export type PreviewContentStatus =
  | "draft"
  | "in_progress"
  | "review"
  | "approved"
  | "ready_to_publish";

export type PreviewCustomer = {
  id: string;
  name: string;
  niche: string;
  audience: string;
  tone: string;
  goals: string;
  platforms: PreviewPlatform[];
  createdAt: string;
  updatedAt: string;
};

export type PreviewContent = {
  id: string;
  customerId: string;
  topic: string;
  platform: PreviewPlatform;
  hook: string;
  body: string;
  cta: string;
  status: PreviewContentStatus;
  origin: "manual" | "demo_generated";
  createdAt: string;
  updatedAt: string;
  submittedAt: string | null;
  approvedAt: string | null;
};

export type PreviewStore = {
  customers: PreviewCustomer[];
  content: PreviewContent[];
};

const STORAGE_KEY = "founder-studio-preview-store-v1";
let memoryStore: PreviewStore | null = null;

export const PREVIEW_PLATFORM_LABEL: Record<PreviewPlatform, string> = {
  tiktok: "TikTok",
  instagram: "Instagram",
  youtube: "YouTube",
};

export const PREVIEW_STATUS_LABEL: Record<PreviewContentStatus, string> = {
  draft: "Draft",
  in_progress: "In Progress",
  review: "Review",
  approved: "Approved",
  ready_to_publish: "Ready to Publish",
};

const SEED: PreviewStore = {
  customers: [
    {
      id: "cust_demo_northwind",
      name: "Northwind Coffee (DEMO)",
      niche: "Specialty coffee for remote workers",
      audience: "Freelancers and small studio owners who work from cafés",
      tone: "Warm, precise, never hype",
      goals: "Weekly short-form that explains brewing without sounding like an ad",
      platforms: ["tiktok", "instagram"],
      createdAt: "2026-08-28T09:00:00.000Z",
      updatedAt: "2026-08-28T09:00:00.000Z",
    },
  ],
  content: [
    {
      id: "cnt_demo_pour_over",
      customerId: "cust_demo_northwind",
      topic: "30-second pour-over for a laptop morning",
      platform: "tiktok",
      hook: "Your pour-over is taking 8 minutes. Steal this 30-second setup.",
      body:
        "DEMO / PREVIEW GENERATED — no AI provider ran.\n\n1. Wet the filter, dump the rinse.\n2. 15g coffee, medium grind.\n3. 240g water, two pours, no swirl theatre.\n4. Drink it before Slack opens.",
      cta: "Save this and try it tomorrow before your first meeting.",
      status: "draft",
      origin: "demo_generated",
      createdAt: "2026-08-28T09:10:00.000Z",
      updatedAt: "2026-08-28T09:10:00.000Z",
      submittedAt: null,
      approvedAt: null,
    },
  ],
};

function nowIso(): string {
  return new Date().toISOString();
}

function newId(prefix: string): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}${Date.now().toString(36)}`;
}

function emptyStore(): PreviewStore {
  return { customers: [], content: [] };
}

function isPlatform(value: unknown): value is PreviewPlatform {
  return value === "tiktok" || value === "instagram" || value === "youtube";
}

function isStatus(value: unknown): value is PreviewContentStatus {
  return (
    value === "draft" ||
    value === "in_progress" ||
    value === "review" ||
    value === "approved" ||
    value === "ready_to_publish"
  );
}

function parseStore(raw: unknown): PreviewStore | null {
  if (!raw || typeof raw !== "object") return null;
  const data = raw as { customers?: unknown; content?: unknown };
  if (!Array.isArray(data.customers) || !Array.isArray(data.content)) return null;
  const customers: PreviewCustomer[] = [];
  for (const item of data.customers) {
    if (!item || typeof item !== "object") return null;
    const row = item as Record<string, unknown>;
    if (typeof row.id !== "string" || typeof row.name !== "string") return null;
    if (!Array.isArray(row.platforms) || !row.platforms.every(isPlatform)) return null;
    customers.push({
      id: row.id,
      name: row.name,
      niche: String(row.niche ?? ""),
      audience: String(row.audience ?? ""),
      tone: String(row.tone ?? ""),
      goals: String(row.goals ?? ""),
      platforms: row.platforms,
      createdAt: String(row.createdAt ?? nowIso()),
      updatedAt: String(row.updatedAt ?? nowIso()),
    });
  }
  const content: PreviewContent[] = [];
  for (const item of data.content) {
    if (!item || typeof item !== "object") return null;
    const row = item as Record<string, unknown>;
    if (typeof row.id !== "string" || typeof row.customerId !== "string") return null;
    if (!isPlatform(row.platform) || !isStatus(row.status)) return null;
    content.push({
      id: row.id,
      customerId: row.customerId,
      topic: String(row.topic ?? ""),
      platform: row.platform,
      hook: String(row.hook ?? ""),
      body: String(row.body ?? ""),
      cta: String(row.cta ?? ""),
      status: row.status,
      origin: row.origin === "demo_generated" ? "demo_generated" : "manual",
      createdAt: String(row.createdAt ?? nowIso()),
      updatedAt: String(row.updatedAt ?? nowIso()),
      submittedAt: typeof row.submittedAt === "string" ? row.submittedAt : null,
      approvedAt: typeof row.approvedAt === "string" ? row.approvedAt : null,
    });
  }
  return { customers, content };
}

function persist(store: PreviewStore): PreviewStore {
  memoryStore = structuredClone(store);
  if (typeof sessionStorage !== "undefined") {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  }
  return store;
}

export function loadPreviewStore(): PreviewStore {
  if (typeof sessionStorage === "undefined") {
    if (!memoryStore) memoryStore = structuredClone(SEED);
    return structuredClone(memoryStore);
  }
  const raw = sessionStorage.getItem(STORAGE_KEY);
  if (!raw) {
    return persist(memoryStore ?? structuredClone(SEED));
  }
  try {
    const parsed = parseStore(JSON.parse(raw) as unknown);
    if (!parsed) {
      return persist(structuredClone(SEED));
    }
    memoryStore = structuredClone(parsed);
    return parsed;
  } catch {
    return persist(structuredClone(SEED));
  }
}

function writeStore(store: PreviewStore): PreviewStore {
  return persist(store);
}

export function resetPreviewStore(): PreviewStore {
  return writeStore(structuredClone(SEED));
}

export function clearPreviewStore(): void {
  memoryStore = null;
  if (typeof sessionStorage !== "undefined") {
    sessionStorage.removeItem(STORAGE_KEY);
  }
}

export function upsertCustomer(
  input: Omit<PreviewCustomer, "id" | "createdAt" | "updatedAt"> & { id?: string },
): PreviewCustomer {
  const store = loadPreviewStore();
  const stamp = nowIso();
  if (input.id) {
    const existing = store.customers.find((row) => row.id === input.id);
    if (!existing) {
      throw new Error("Preview customer not found.");
    }
    const updated: PreviewCustomer = {
      ...existing,
      name: input.name,
      niche: input.niche,
      audience: input.audience,
      tone: input.tone,
      goals: input.goals,
      platforms: input.platforms,
      updatedAt: stamp,
    };
    writeStore({
      ...store,
      customers: store.customers.map((row) => (row.id === updated.id ? updated : row)),
    });
    return updated;
  }
  const created: PreviewCustomer = {
    id: newId("cust"),
    name: input.name,
    niche: input.niche,
    audience: input.audience,
    tone: input.tone,
    goals: input.goals,
    platforms: input.platforms,
    createdAt: stamp,
    updatedAt: stamp,
  };
  writeStore({ ...store, customers: [created, ...store.customers] });
  return created;
}

export function upsertContent(
  input: Omit<PreviewContent, "id" | "createdAt" | "updatedAt" | "submittedAt" | "approvedAt"> & {
    id?: string;
  },
): PreviewContent {
  const store = loadPreviewStore();
  if (!store.customers.some((row) => row.id === input.customerId)) {
    throw new Error("Choose a preview customer before saving content.");
  }
  const stamp = nowIso();
  if (input.id) {
    const existing = store.content.find((row) => row.id === input.id);
    if (!existing) {
      throw new Error("Preview content not found.");
    }
    if (existing.status === "ready_to_publish") {
      throw new Error("Ready-to-publish items are locked. Nothing was published.");
    }
    const updated: PreviewContent = {
      ...existing,
      customerId: input.customerId,
      topic: input.topic,
      platform: input.platform,
      hook: input.hook,
      body: input.body,
      cta: input.cta,
      status: existing.status === "approved" ? existing.status : input.status === "review" ? "review" : "in_progress",
      origin: input.origin,
      updatedAt: stamp,
    };
    writeStore({
      ...store,
      content: store.content.map((row) => (row.id === updated.id ? updated : row)),
    });
    return updated;
  }
  const created: PreviewContent = {
    id: newId("cnt"),
    customerId: input.customerId,
    topic: input.topic,
    platform: input.platform,
    hook: input.hook,
    body: input.body,
    cta: input.cta,
    status: "draft",
    origin: input.origin,
    createdAt: stamp,
    updatedAt: stamp,
    submittedAt: null,
    approvedAt: null,
  };
  writeStore({ ...store, content: [created, ...store.content] });
  return created;
}

export function submitPreviewForReview(id: string): PreviewContent {
  const store = loadPreviewStore();
  const existing = store.content.find((row) => row.id === id);
  if (!existing) {
    throw new Error("Preview content not found.");
  }
  if (existing.status === "ready_to_publish") {
    throw new Error("This item is already in Ready to Publish. Nothing was posted.");
  }
  const stamp = nowIso();
  const updated: PreviewContent = {
    ...existing,
    status: "review",
    submittedAt: stamp,
    updatedAt: stamp,
  };
  writeStore({
    ...store,
    content: store.content.map((row) => (row.id === id ? updated : row)),
  });
  return updated;
}

/** Deliberate Founder approval. Moves the exact item into Ready to Publish. Never publishes. */
export function approvePreviewContent(id: string): PreviewContent {
  const store = loadPreviewStore();
  const existing = store.content.find((row) => row.id === id);
  if (!existing) {
    throw new Error("Preview content not found.");
  }
  if (existing.status !== "review") {
    throw new Error("Only items in Review can be approved.");
  }
  const stamp = nowIso();
  const updated: PreviewContent = {
    ...existing,
    status: "ready_to_publish",
    approvedAt: stamp,
    updatedAt: stamp,
  };
  writeStore({
    ...store,
    content: store.content.map((row) => (row.id === id ? updated : row)),
  });
  return updated;
}

export function customerById(store: PreviewStore, id: string): PreviewCustomer | undefined {
  return store.customers.find((row) => row.id === id);
}

export function contentInReview(store: PreviewStore): PreviewContent[] {
  return store.content.filter((row) => row.status === "review");
}

export function contentReadyToPublish(store: PreviewStore): PreviewContent[] {
  return store.content.filter((row) => row.status === "ready_to_publish");
}

export function emptyPreviewStoreForTests(): PreviewStore {
  return emptyStore();
}
