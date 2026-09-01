import { useMemo, useState, type FormEvent, type ReactNode } from "react";

import {
  approvePreviewContent,
  contentInReview,
  contentReadyToPublish,
  customerById,
  loadPreviewStore,
  PREVIEW_PLATFORM_LABEL,
  PREVIEW_STATUS_LABEL,
  resetPreviewStore,
  submitPreviewForReview,
  upsertContent,
  upsertCustomer,
  type PreviewContent,
  type PreviewPlatform,
  type PreviewStore,
} from "./preview/store";

type FounderNav = "dashboard" | "customers" | "create" | "review" | "ready";

const PLATFORMS: PreviewPlatform[] = ["tiktok", "instagram", "youtube"];

function formatWhen(value: string | null): string {
  if (!value) return "Not yet";
  return new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

function usePreviewRevision() {
  const [revision, setRevision] = useState(0);
  const store = useMemo(() => loadPreviewStore(), [revision]);
  const refresh = () => setRevision((value) => value + 1);
  return { store, refresh };
}

function Chip({ children, tone = "gold" }: { children: ReactNode; tone?: "gold" | "ink" | "warn" }) {
  return <span className={`founder-chip founder-chip--${tone}`}>{children}</span>;
}

function nextDesk(store: PreviewStore): { go: FounderNav; title: string; detail: string; cta: string } {
  if (store.customers.length === 0) {
    return {
      go: "customers",
      title: "Add the first brand",
      detail: "A piece of content has to belong to a customer. Start with a fake brand you can direct.",
      cta: "Open Customers",
    };
  }
  if (contentInReview(store).length > 0) {
    return {
      go: "review",
      title: "You have work waiting",
      detail: "Read it as the creative director. Approve only if you would put your name on it.",
      cta: "Open Review",
    };
  }
  return {
    go: "create",
    title: "Write the next piece",
    detail: "AI PROVIDER NOT CONFIGURED. Write the hook and script yourself, or insert labelled DEMO copy.",
    cta: "Create content",
  };
}

function PostStage({
  customer,
  platform,
  hook,
  body,
  cta,
}: {
  customer: string;
  platform: PreviewPlatform;
  hook: string;
  body: string;
  cta: string;
}) {
  return (
    <aside className="founder-stage" aria-label="On-phone preview">
      <div className="founder-stage__bezel">
        <div className="founder-stage__notch" />
        <p className="founder-stage__brand">{customer || "Customer"}</p>
        <p className="founder-stage__platform">{PREVIEW_PLATFORM_LABEL[platform]}</p>
        <h3>{hook || "The hook will appear here."}</h3>
        <p>{body || "Write the caption or script. This is how it will read on a phone."}</p>
        <span>{cta || "Add a CTA"}</span>
      </div>
    </aside>
  );
}

export function FounderPreviewBanner() {
  return (
    <aside className="founder-banner" role="status">
      <strong>Founder Studio preview</strong>
      <p>
        Browser-local demo data. The fake Continue token is never sent to FastAPI. Nothing publishes.
        External AI providers are not configured.
      </p>
    </aside>
  );
}

export function FounderHomeView({ navigate }: { navigate: (key: FounderNav) => void }) {
  const { store } = usePreviewRevision();
  const review = contentInReview(store);
  const ready = contentReadyToPublish(store);
  const next = nextDesk(store);

  return (
    <div className="founder-page">
      <FounderPreviewBanner />
      <header className="founder-hero">
        <p className="page-kicker">Founder Studio</p>
        <h2>Home</h2>
        <p>You are the creative director. Create the work, review it, then approve it into Ready to Publish.</p>
      </header>
      <button className="founder-next" onClick={() => navigate(next.go)} type="button">
        <span>Next</span>
        <strong>{next.title}</strong>
        <p>{next.detail}</p>
        <b>{next.cta}</b>
      </button>
      <div className="founder-stat-grid">
        <button className="founder-stat" onClick={() => navigate("customers")} type="button">
          <span>Customers</span>
          <strong>{store.customers.length}</strong>
        </button>
        <button className="founder-stat" onClick={() => navigate("review")} type="button">
          <span>Waiting for review</span>
          <strong>{review.length}</strong>
        </button>
        <button className="founder-stat" onClick={() => navigate("ready")} type="button">
          <span>Ready to publish</span>
          <strong>{ready.length}</strong>
        </button>
      </div>
      <section className="founder-card">
        <h3>Today&apos;s workflow</h3>
        <ol className="founder-steps">
          <li>Open Customers and add a fake customer brand.</li>
          <li>Create or edit a content item. Write it yourself — AI is not connected.</li>
          <li>Submit it for review, then press APPROVE.</li>
          <li>Confirm it appears in Ready to Publish. It is not posted anywhere.</li>
        </ol>
        <div className="founder-actions">
          <button className="button button--primary founder-tap" onClick={() => navigate("customers")} type="button">
            Open Customers
          </button>
          <button className="button founder-tap" onClick={() => navigate("create")} type="button">
            Create content
          </button>
        </div>
      </section>
      <p className="founder-footnote">AI PROVIDER NOT CONFIGURED. Manual writing or labelled DEMO copy only.</p>
    </div>
  );
}

export function FounderCustomersView() {
  const { store, refresh } = usePreviewRevision();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const editing = store.customers.find((row) => row.id === editingId) ?? null;

  function onSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const platforms = PLATFORMS.filter((platform) => form.get(platform) === "on");
    const name = String(form.get("name") ?? "").trim();
    if (!name) {
      setError("Customer name is required.");
      return;
    }
    if (platforms.length === 0) {
      setError("Choose at least one target platform.");
      return;
    }
    try {
      upsertCustomer({
        id: editing?.id,
        name,
        niche: String(form.get("niche") ?? "").trim(),
        audience: String(form.get("audience") ?? "").trim(),
        tone: String(form.get("tone") ?? "").trim(),
        goals: String(form.get("goals") ?? "").trim(),
        platforms,
      });
      setError(null);
      setEditingId(null);
      event.currentTarget.reset();
      refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not save customer.");
    }
  }

  return (
    <div className="founder-page">
      <FounderPreviewBanner />
      <header className="founder-hero">
        <p className="page-kicker">Customers</p>
        <h2>{editing ? "Edit brand profile" : "Create a fake customer"}</h2>
        <p>Brand details stay in this browser tab. They are not written to Supabase.</p>
      </header>
      <form className="founder-card founder-form" onSubmit={onSave}>
        <label>
          Customer / business name
          <input defaultValue={editing?.name ?? ""} name="name" required />
        </label>
        <label>
          Niche
          <input defaultValue={editing?.niche ?? ""} name="niche" />
        </label>
        <label>
          Target audience
          <textarea defaultValue={editing?.audience ?? ""} name="audience" rows={3} />
        </label>
        <label>
          Brand tone
          <input defaultValue={editing?.tone ?? ""} name="tone" />
        </label>
        <label>
          Goals
          <textarea defaultValue={editing?.goals ?? ""} name="goals" rows={3} />
        </label>
        <fieldset className="founder-platforms">
          <legend>Target platforms</legend>
          {PLATFORMS.map((platform) => (
            <label className="founder-check" key={platform}>
              <input
                defaultChecked={editing?.platforms.includes(platform) ?? platform !== "youtube"}
                name={platform}
                type="checkbox"
              />
              {PREVIEW_PLATFORM_LABEL[platform]}
            </label>
          ))}
        </fieldset>
        {error ? <p className="error" role="alert">{error}</p> : null}
        <div className="founder-actions">
          <button className="button button--primary founder-tap" type="submit">
            {editing ? "Save brand" : "Save fake customer"}
          </button>
          {editing ? (
            <button className="button founder-tap" onClick={() => setEditingId(null)} type="button">
              Cancel
            </button>
          ) : null}
        </div>
      </form>
      <section className="founder-card">
        <h3>Customers in this preview</h3>
        {store.customers.length === 0 ? (
          <p>No customers yet. Add one above.</p>
        ) : (
          <ul className="founder-list">
            {store.customers.map((customer) => (
              <li className="founder-brand-row" key={customer.id}>
                <span className="founder-mono" aria-hidden="true">{customer.name.slice(0, 1).toUpperCase()}</span>
                <div>
                  <strong>{customer.name}</strong>
                  <small>{customer.niche || "No niche"}</small>
                  <div className="founder-chip-row">
                    {customer.platforms.map((platform) => (
                      <Chip key={platform}>{PREVIEW_PLATFORM_LABEL[platform]}</Chip>
                    ))}
                  </div>
                </div>
                <button className="button founder-tap" onClick={() => setEditingId(customer.id)} type="button">
                  Edit brand
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

const EMPTY_DRAFT = {
  customerId: "",
  topic: "",
  platform: "tiktok" as PreviewPlatform,
  hook: "",
  body: "",
  cta: "",
};

export function FounderCreateView() {
  const { store, refresh } = usePreviewRevision();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [draft, setDraft] = useState(EMPTY_DRAFT);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const editing = store.content.find((row) => row.id === editingId) ?? null;
  const activeCustomer = customerById(store, draft.customerId || store.customers[0]?.id || "");

  function startEdit(item: PreviewContent) {
    setEditingId(item.id);
    setDraft({
      customerId: item.customerId,
      topic: item.topic,
      platform: item.platform,
      hook: item.hook,
      body: item.body,
      cta: item.cta,
    });
    setNotice(null);
    setError(null);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function insertDemoCopy() {
    const customer = customerById(store, draft.customerId) ?? store.customers[0];
    setDraft((current) => ({
      ...current,
      customerId: current.customerId || customer?.id || "",
      topic: current.topic || "Demo idea: one useful tip for this brand",
      hook: "DEMO / PREVIEW GENERATED — your audience stops scrolling for a useful rule, not a slogan.",
      body:
        "DEMO / PREVIEW GENERATED — no AI provider ran.\n\nWrite the real script here. This block exists so the Founder can test the editor when providers are not configured.",
      cta: "Save this. Do not treat it as a live generation.",
    }));
    setNotice("Inserted labelled DEMO copy. AI PROVIDER NOT CONFIGURED.");
  }

  function onSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const customerId = draft.customerId || store.customers[0]?.id || "";
    if (!customerId) {
      setError("Choose a customer first.");
      return;
    }
    if (!draft.topic.trim() || !draft.hook.trim() || !draft.body.trim()) {
      setError("Topic, hook, and body are required.");
      return;
    }
    try {
      const saved = upsertContent({
        id: editing?.id,
        customerId,
        topic: draft.topic.trim(),
        platform: draft.platform,
        hook: draft.hook.trim(),
        body: draft.body.trim(),
        cta: draft.cta.trim(),
        status: editing?.status === "review" ? "review" : "draft",
        origin: draft.body.includes("DEMO / PREVIEW GENERATED") ? "demo_generated" : "manual",
      });
      setError(null);
      setNotice(`Saved as ${PREVIEW_STATUS_LABEL[saved.status]}. Nothing was published.`);
      setEditingId(null);
      setDraft({ ...EMPTY_DRAFT, customerId: draft.customerId, platform: draft.platform });
      refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not save content.");
    }
  }

  function sendToReview(id: string) {
    try {
      submitPreviewForReview(id);
      setNotice("Submitted for review. Approve it on the Review screen.");
      setError(null);
      refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not submit for review.");
    }
  }

  return (
    <div className="founder-page">
      <FounderPreviewBanner />
      <header className="founder-hero">
        <p className="page-kicker">Create</p>
        <h2>{editing ? "Edit content" : "Create content"}</h2>
        <p>Write the piece yourself. Generation providers are not approved for live use.</p>
      </header>
      <p className="founder-callout" role="status">AI PROVIDER NOT CONFIGURED</p>
      {store.customers.length === 0 ? (
        <section className="founder-card">
          <h3>Add a customer first</h3>
          <p>Content must belong to a fake customer brand.</p>
        </section>
      ) : (
        <div className="founder-create-grid">
          <form className="founder-card founder-form" onSubmit={onSave}>
            <label>
              Customer
              <select
                aria-label="Customer"
                onChange={(event) => setDraft((current) => ({ ...current, customerId: event.target.value }))}
                value={draft.customerId || store.customers[0]?.id || ""}
              >
                {store.customers.map((customer) => (
                  <option key={customer.id} value={customer.id}>{customer.name}</option>
                ))}
              </select>
            </label>
            <label>
              Idea / topic
              <input
                onChange={(event) => setDraft((current) => ({ ...current, topic: event.target.value }))}
                value={draft.topic}
              />
            </label>
            <fieldset className="founder-segment">
              <legend>Platform</legend>
              <div className="founder-segment__row" role="group" aria-label="Platform">
                {PLATFORMS.map((platform) => (
                  <button
                    className={draft.platform === platform ? "founder-segment__btn founder-segment__btn--on" : "founder-segment__btn"}
                    key={platform}
                    onClick={() => setDraft((current) => ({ ...current, platform }))}
                    type="button"
                  >
                    {PREVIEW_PLATFORM_LABEL[platform]}
                  </button>
                ))}
              </div>
            </fieldset>
            <label>
              Hook
              <textarea
                onChange={(event) => setDraft((current) => ({ ...current, hook: event.target.value }))}
                rows={3}
                value={draft.hook}
              />
            </label>
            <label>
              Caption / script / body
              <textarea
                onChange={(event) => setDraft((current) => ({ ...current, body: event.target.value }))}
                rows={8}
                value={draft.body}
              />
            </label>
            <label>
              CTA
              <input
                onChange={(event) => setDraft((current) => ({ ...current, cta: event.target.value }))}
                value={draft.cta}
              />
            </label>
            {error ? <p className="error" role="alert">{error}</p> : null}
            {notice ? <p className="founder-notice" role="status">{notice}</p> : null}
            <div className="founder-actions">
              <button className="button button--primary founder-tap" type="submit">
                {editing ? "Save edits" : "Save draft"}
              </button>
              <button className="button founder-tap" onClick={insertDemoCopy} type="button">
                Insert DEMO copy
              </button>
              {editing ? (
                <button className="button founder-tap" onClick={() => { setEditingId(null); setDraft(EMPTY_DRAFT); }} type="button">
                  New item
                </button>
              ) : null}
            </div>
          </form>
          <PostStage
            body={draft.body}
            cta={draft.cta}
            customer={activeCustomer?.name ?? "Customer"}
            hook={draft.hook}
            platform={draft.platform}
          />
        </div>
      )}
      <section className="founder-card">
        <h3>Content in this preview</h3>
        <ul className="founder-list">
          {store.content.map((item) => {
            const customer = customerById(store, item.customerId);
            return (
              <li key={item.id}>
                <div>
                  <strong>{item.topic}</strong>
                  <small>
                    {customer?.name ?? "Unknown customer"} · {PREVIEW_PLATFORM_LABEL[item.platform]} · {PREVIEW_STATUS_LABEL[item.status]}
                    {item.origin === "demo_generated" ? " · DEMO" : ""}
                  </small>
                </div>
                <div className="founder-actions founder-actions--compact">
                  {item.status !== "ready_to_publish" ? (
                    <button className="button founder-tap" onClick={() => startEdit(item)} type="button">Edit</button>
                  ) : null}
                  {item.status === "draft" || item.status === "in_progress" ? (
                    <button className="button button--primary founder-tap" onClick={() => sendToReview(item.id)} type="button">
                      Submit for review
                    </button>
                  ) : null}
                </div>
              </li>
            );
          })}
        </ul>
      </section>
    </div>
  );
}

export function FounderReviewView() {
  const { store, refresh } = usePreviewRevision();
  const queue = contentInReview(store);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  function approve(item: PreviewContent) {
    try {
      approvePreviewContent(item.id);
      setError(null);
      setNotice(`Approved “${item.topic}”. Moved to Ready to Publish. No platform was called.`);
      refresh();
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Approval failed.");
    }
  }

  return (
    <div className="founder-page">
      <FounderPreviewBanner />
      <header className="founder-hero">
        <p className="page-kicker">Human review</p>
        <h2>Review</h2>
        <p>Approval is a deliberate Founder action. It queues the exact item. It does not publish.</p>
      </header>
      {error ? <p className="error" role="alert">{error}</p> : null}
      {notice ? <p className="founder-notice" role="status">{notice}</p> : null}
      {queue.length === 0 ? (
        <section className="founder-card">
          <h3>Nothing waiting</h3>
          <p>Create a draft and press Submit for review. The Human Review Gate is not bypassed.</p>
        </section>
      ) : (
        <ul className="founder-review-list">
          {queue.map((item) => {
            const customer = customerById(store, item.customerId);
            return (
              <li className="founder-card founder-review-card" key={item.id}>
                <p className="founder-meta">
                  {customer?.name ?? "Unknown customer"} · {PREVIEW_PLATFORM_LABEL[item.platform]} · submitted {formatWhen(item.submittedAt)}
                </p>
                <h3>{item.topic}</h3>
                <PostStage
                  body={item.body}
                  cta={item.cta}
                  customer={customer?.name ?? "Unknown customer"}
                  hook={item.hook}
                  platform={item.platform}
                />
                <p><strong>Hook</strong> {item.hook}</p>
                <pre className="founder-script">{item.body}</pre>
                <p><strong>CTA</strong> {item.cta}</p>
                <button className="button button--primary founder-tap founder-approve" onClick={() => approve(item)} type="button">
                  APPROVE
                </button>
                <p className="founder-footnote">APPROVE holds this piece. It does not post it.</p>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export function FounderReadyView() {
  const { store } = usePreviewRevision();
  const queue = contentReadyToPublish(store);

  return (
    <div className="founder-page">
      <FounderPreviewBanner />
      <header className="founder-hero">
        <p className="page-kicker">Queue</p>
        <h2>Ready to Publish</h2>
        <p>Approved by the Founder. Held here. No social API is called from this screen.</p>
      </header>
      {queue.length === 0 ? (
        <section className="founder-card">
          <h3>Queue empty</h3>
          <p>Approved items will appear here. Nothing has been posted.</p>
        </section>
      ) : (
        <ul className="founder-review-list">
          {queue.map((item) => {
            const customer = customerById(store, item.customerId);
            return (
              <li className="founder-card founder-held" key={item.id}>
                <div className="founder-held__seal">Held</div>
                <p className="founder-meta">
                  {customer?.name ?? "Unknown customer"} · {PREVIEW_PLATFORM_LABEL[item.platform]} · approved {formatWhen(item.approvedAt)}
                </p>
                <h3>{item.topic}</h3>
                <p>{item.hook}</p>
                <pre className="founder-script">{item.body}</pre>
                <p className="founder-callout">Approved · not published · no social platform API called</p>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export function FounderSettingsView() {
  const { refresh } = usePreviewRevision();
  return (
    <div className="founder-page">
      <FounderPreviewBanner />
      <header className="founder-hero">
        <p className="page-kicker">Settings</p>
        <h2>Preview controls</h2>
      </header>
      <section className="founder-card">
        <h3>What this preview is</h3>
        <ul className="founder-bullets">
          <li>UI-only Continue session. Token <code>founder-studio-preview-ui-only</code> is never accepted by FastAPI.</li>
          <li>Customers and content persist in <code>sessionStorage</code> for this tab.</li>
          <li>RLS, Human Review, and production auth are unchanged.</li>
          <li>Resetting demo data does not touch Supabase.</li>
        </ul>
        <button
          className="button founder-tap"
          onClick={() => {
            resetPreviewStore();
            refresh();
          }}
          type="button"
        >
          Reset demo data
        </button>
      </section>
    </div>
  );
}

export function FounderAdvancedUnavailable({ label }: { label: string }) {
  return (
    <div className="founder-page">
      <FounderPreviewBanner />
      <section className="founder-card">
        <h2>{label}</h2>
        <p>
          This operational desk view talks to the real authenticated API. The Founder Studio
          Continue session is UI-only, so this screen is not connected in preview.
        </p>
        <p className="founder-callout">Use Home, Customers, Create, Review, and Ready to Publish for the Android test.</p>
      </section>
    </div>
  );
}
