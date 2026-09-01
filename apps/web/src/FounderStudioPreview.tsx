import { useMemo, useState, type FormEvent } from "react";
import { BusinessManagerMark } from "./BusinessManagerMark";
import "./founderStudioPreview.css";

type Screen = "home" | "customers" | "create" | "review" | "ready";
type Platform = "Instagram" | "TikTok" | "YouTube";
type ContentStatus = "draft" | "review" | "ready_to_publish";

type Customer = {
  id: string;
  name: string;
  niche: string;
  audience: string;
  tone: string;
  goals: string;
  platforms: Platform[];
};

type ContentItem = {
  id: string;
  customerId: string;
  platform: Platform;
  idea: string;
  hook: string;
  body: string;
  cta: string;
  status: ContentStatus;
  version: number;
  updatedAt: string;
};

type PreviewStore = {
  customers: Customer[];
  content: ContentItem[];
};

type Props = {
  onExit: () => void;
};

const STORE_KEY = "content-orchestrator.founder-studio.preview.v1";
const EMPTY_STORE: PreviewStore = { customers: [], content: [] };

function makeId(prefix: string): string {
  return `${prefix}-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

function loadStore(): PreviewStore {
  try {
    const raw = localStorage.getItem(STORE_KEY);
    if (!raw) return EMPTY_STORE;
    const parsed = JSON.parse(raw) as PreviewStore;
    if (!Array.isArray(parsed.customers) || !Array.isArray(parsed.content)) return EMPTY_STORE;
    return parsed;
  } catch {
    return EMPTY_STORE;
  }
}

function customerName(customers: Customer[], id: string): string {
  return customers.find((customer) => customer.id === id)?.name ?? "Unknown customer";
}

export default function FounderStudioPreview({ onExit }: Props) {
  const [screen, setScreen] = useState<Screen>("home");
  const [store, setStore] = useState<PreviewStore>(() => loadStore());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const reviewItems = useMemo(
    () => store.content.filter((item) => item.status === "review"),
    [store.content],
  );
  const readyItems = useMemo(
    () => store.content.filter((item) => item.status === "ready_to_publish"),
    [store.content],
  );
  const drafts = useMemo(
    () => store.content.filter((item) => item.status === "draft"),
    [store.content],
  );

  function persist(next: PreviewStore) {
    localStorage.setItem(STORE_KEY, JSON.stringify(next));
    setStore(next);
  }

  function navigate(next: Screen) {
    setNotice(null);
    if (next !== "create") setEditingId(null);
    setScreen(next);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function resetPreview() {
    if (!window.confirm("Reset all Founder Studio preview customers and content?")) return;
    localStorage.removeItem(STORE_KEY);
    setStore(EMPTY_STORE);
    setEditingId(null);
    setNotice("Preview data reset.");
    setScreen("home");
  }

  function editContent(id: string) {
    setEditingId(id);
    setNotice(null);
    setScreen("create");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function approveContent(id: string) {
    const now = new Date().toISOString();
    persist({
      ...store,
      content: store.content.map((item) =>
        item.id === id
          ? { ...item, status: "ready_to_publish", updatedAt: now }
          : item,
      ),
    });
    setNotice("Approved. The exact current version is now Ready to Publish. Nothing was posted externally.");
  }

  return (
    <div className="fsp-shell">
      <header className="fsp-header">
        <div className="fsp-brand">
          <BusinessManagerMark className="fsp-brand__mark" />
          <div>
            <strong>The Business Manager</strong>
            <span>Founder Studio Preview</span>
          </div>
        </div>
        <button className="fsp-header__exit" type="button" onClick={onExit}>Exit</button>
      </header>

      <div className="fsp-preview-banner" role="status">
        <strong>PREVIEW MODE</strong>
        <span>Browser-local test data only · AI provider not configured · external publishing disabled</span>
      </div>

      <main className="fsp-main">
        {notice ? <div className="fsp-notice" role="status">{notice}</div> : null}

        {screen === "home" ? (
          <Home
            customers={store.customers.length}
            drafts={drafts.length}
            review={reviewItems.length}
            ready={readyItems.length}
            navigate={navigate}
          />
        ) : null}

        {screen === "customers" ? (
          <CustomersScreen
            customers={store.customers}
            onSave={(customer) => {
              persist({ ...store, customers: [...store.customers, customer] });
              setNotice(`${customer.name} added. You can create content for them now.`);
            }}
            onCreateContent={() => navigate("create")}
          />
        ) : null}

        {screen === "create" ? (
          <CreateScreen
            customers={store.customers}
            editing={store.content.find((item) => item.id === editingId) ?? null}
            onCancel={() => navigate("home")}
            onSave={(item) => {
              const exists = store.content.some((current) => current.id === item.id);
              const content = exists
                ? store.content.map((current) => (current.id === item.id ? item : current))
                : [item, ...store.content];
              persist({ ...store, content });
              setEditingId(null);
              setNotice(item.status === "review" ? "Content sent to Human Review." : "Draft saved on this device.");
              setScreen(item.status === "review" ? "review" : "home");
            }}
          />
        ) : null}

        {screen === "review" ? (
          <QueueScreen
            title="Human Review"
            emptyTitle="Nothing waiting for review"
            emptyCopy="Create content and send it to review when you are happy with the draft."
            items={reviewItems}
            customers={store.customers}
            actionLabel="APPROVE"
            onAction={approveContent}
            onEdit={editContent}
          />
        ) : null}

        {screen === "ready" ? (
          <ReadyScreen items={readyItems} customers={store.customers} onEdit={editContent} />
        ) : null}
      </main>

      <nav className="fsp-nav" aria-label="Founder Studio navigation">
        <NavButton label="Home" active={screen === "home"} onClick={() => navigate("home")} />
        <NavButton label="Customers" active={screen === "customers"} onClick={() => navigate("customers")} />
        <NavButton label="Create" active={screen === "create"} onClick={() => navigate("create")} />
        <NavButton label={`Review${reviewItems.length ? ` ${reviewItems.length}` : ""}`} active={screen === "review"} onClick={() => navigate("review")} />
        <NavButton label={`Ready${readyItems.length ? ` ${readyItems.length}` : ""}`} active={screen === "ready"} onClick={() => navigate("ready")} />
      </nav>

      <button className="fsp-reset" type="button" onClick={resetPreview}>Reset preview data</button>
    </div>
  );
}

function NavButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return <button className={active ? "fsp-nav__button fsp-nav__button--active" : "fsp-nav__button"} type="button" onClick={onClick}>{label}</button>;
}

function Home({
  customers,
  drafts,
  review,
  ready,
  navigate,
}: {
  customers: number;
  drafts: number;
  review: number;
  ready: number;
  navigate: (screen: Screen) => void;
}) {
  return (
    <div className="fsp-stack">
      <section className="fsp-hero">
        <p className="fsp-kicker">Founder Studio</p>
        <h1>Create awesome customer content yourself.</h1>
        <p>Use the studio as your AI-assisted production desk. You stay the creative director and nothing publishes without your approval.</p>
        <div className="fsp-actions">
          <button className="fsp-button fsp-button--primary" type="button" onClick={() => navigate(customers ? "create" : "customers")}>{customers ? "CREATE CONTENT" : "ADD FIRST CUSTOMER"}</button>
          <button className="fsp-button" type="button" onClick={() => navigate("review")}>OPEN REVIEW</button>
        </div>
      </section>

      <section className="fsp-metrics" aria-label="Founder Studio summary">
        <Metric label="Customers" value={customers} />
        <Metric label="Drafts" value={drafts} />
        <Metric label="In review" value={review} />
        <Metric label="Ready" value={ready} />
      </section>

      <section className="fsp-card">
        <p className="fsp-kicker">First test</p>
        <h2>Run the whole workflow</h2>
        <ol className="fsp-checklist">
          <li className={customers ? "done" : ""}>Create a fake customer</li>
          <li className={drafts + review + ready ? "done" : ""}>Write and edit a content item</li>
          <li className={review + ready ? "done" : ""}>Send it to Human Review</li>
          <li className={ready ? "done" : ""}>Approve the exact version</li>
          <li className={ready ? "done" : ""}>See it in Ready to Publish</li>
        </ol>
      </section>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return <article><strong>{value}</strong><span>{label}</span></article>;
}

function CustomersScreen({
  customers,
  onSave,
  onCreateContent,
}: {
  customers: Customer[];
  onSave: (customer: Customer) => void;
  onCreateContent: () => void;
}) {
  const [name, setName] = useState("");
  const [niche, setNiche] = useState("");
  const [audience, setAudience] = useState("");
  const [tone, setTone] = useState("");
  const [goals, setGoals] = useState("");
  const [platforms, setPlatforms] = useState<Platform[]>(["Instagram"]);

  function togglePlatform(platform: Platform) {
    setPlatforms((current) => current.includes(platform) ? current.filter((item) => item !== platform) : [...current, platform]);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    if (!platforms.length) return;
    onSave({ id: makeId("customer"), name: name.trim(), niche: niche.trim(), audience: audience.trim(), tone: tone.trim(), goals: goals.trim(), platforms });
    setName("");
    setNiche("");
    setAudience("");
    setTone("");
    setGoals("");
    setPlatforms(["Instagram"]);
  }

  return (
    <div className="fsp-stack">
      <section className="fsp-page-heading"><p className="fsp-kicker">Customers</p><h1>Brand profiles</h1><p>Keep each customer’s niche, audience, voice and goals together before you create their content.</p></section>
      <form className="fsp-card fsp-form" onSubmit={submit}>
        <h2>Add customer</h2>
        <label>Business / customer name<input value={name} onChange={(event) => setName(event.target.value)} required placeholder="e.g. Apex Fitness" /></label>
        <label>Niche<input value={niche} onChange={(event) => setNiche(event.target.value)} required placeholder="e.g. Online fitness coaching" /></label>
        <label>Target audience<textarea value={audience} onChange={(event) => setAudience(event.target.value)} required placeholder="Who are we creating for?" /></label>
        <label>Brand tone<input value={tone} onChange={(event) => setTone(event.target.value)} required placeholder="e.g. Direct, motivating, premium" /></label>
        <label>Goals<textarea value={goals} onChange={(event) => setGoals(event.target.value)} required placeholder="What should the content achieve?" /></label>
        <fieldset><legend>Target platforms</legend><div className="fsp-platforms">{(["Instagram", "TikTok", "YouTube"] as Platform[]).map((platform) => <button className={platforms.includes(platform) ? "selected" : ""} key={platform} type="button" onClick={() => togglePlatform(platform)}>{platform}</button>)}</div></fieldset>
        <button className="fsp-button fsp-button--primary" type="submit">SAVE CUSTOMER</button>
      </form>

      <section className="fsp-stack">
        {customers.map((customer) => (
          <article className="fsp-card fsp-customer" key={customer.id}>
            <div><span className="fsp-chip">PREVIEW CUSTOMER</span><h2>{customer.name}</h2><p>{customer.niche}</p></div>
            <dl><div><dt>Audience</dt><dd>{customer.audience}</dd></div><div><dt>Tone</dt><dd>{customer.tone}</dd></div><div><dt>Goals</dt><dd>{customer.goals}</dd></div></dl>
            <div className="fsp-tags">{customer.platforms.map((platform) => <span key={platform}>{platform}</span>)}</div>
            <button className="fsp-button" type="button" onClick={onCreateContent}>CREATE CONTENT</button>
          </article>
        ))}
      </section>
    </div>
  );
}

function CreateScreen({
  customers,
  editing,
  onSave,
  onCancel,
}: {
  customers: Customer[];
  editing: ContentItem | null;
  onSave: (item: ContentItem) => void;
  onCancel: () => void;
}) {
  const first = customers[0];
  const [customerId, setCustomerId] = useState(editing?.customerId ?? first?.id ?? "");
  const customer = customers.find((item) => item.id === customerId) ?? first;
  const [platform, setPlatform] = useState<Platform>(editing?.platform ?? customer?.platforms[0] ?? "Instagram");
  const [idea, setIdea] = useState(editing?.idea ?? "");
  const [hook, setHook] = useState(editing?.hook ?? "");
  const [body, setBody] = useState(editing?.body ?? "");
  const [cta, setCta] = useState(editing?.cta ?? "");

  if (!customers.length) {
    return <section className="fsp-card fsp-empty"><h1>Add a customer first</h1><p>A brand profile is required before creating customer content.</p><button className="fsp-button fsp-button--primary" type="button" onClick={onCancel}>BACK HOME</button></section>;
  }

  function build(status: ContentStatus): ContentItem {
    const changed = Boolean(editing) && (editing!.customerId !== customerId || editing!.platform !== platform || editing!.idea !== idea || editing!.hook !== hook || editing!.body !== body || editing!.cta !== cta);
    return {
      id: editing?.id ?? makeId("content"),
      customerId,
      platform,
      idea: idea.trim(),
      hook: hook.trim(),
      body: body.trim(),
      cta: cta.trim(),
      status,
      version: editing ? editing.version + (changed ? 1 : 0) : 1,
      updatedAt: new Date().toISOString(),
    };
  }

  return (
    <div className="fsp-stack">
      <section className="fsp-page-heading"><p className="fsp-kicker">Create</p><h1>{editing ? `Edit content · v${editing.version}` : "Create customer content"}</h1><p>You write and shape the content. AI generation is deliberately not pretending to be connected in this preview.</p></section>
      <div className="fsp-provider-warning"><strong>AI PROVIDER NOT CONFIGURED</strong><span>Manual content creation is available now. No provider calls or spend will occur.</span></div>
      <form className="fsp-card fsp-form" onSubmit={(event) => { event.preventDefault(); onSave(build("review")); }}>
        <label>Customer<select value={customerId} onChange={(event) => { const nextId = event.target.value; setCustomerId(nextId); const nextCustomer = customers.find((item) => item.id === nextId); if (nextCustomer?.platforms[0]) setPlatform(nextCustomer.platforms[0]); }}>{customers.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
        <label>Platform<select value={platform} onChange={(event) => setPlatform(event.target.value as Platform)}>{(customer?.platforms ?? ["Instagram", "TikTok", "YouTube"]).map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
        <label>Idea / topic<textarea value={idea} onChange={(event) => setIdea(event.target.value)} required placeholder="What is this piece of content about?" /></label>
        <label>Hook<textarea value={hook} onChange={(event) => setHook(event.target.value)} required placeholder="First line that earns attention" /></label>
        <label>Script / caption<textarea className="fsp-editor" value={body} onChange={(event) => setBody(event.target.value)} required placeholder="Write the main content here…" /></label>
        <label>Call to action<textarea value={cta} onChange={(event) => setCta(event.target.value)} required placeholder="What should the viewer do next?" /></label>
        <div className="fsp-form-actions"><button className="fsp-button" type="button" onClick={() => onSave(build("draft"))}>SAVE DRAFT</button><button className="fsp-button fsp-button--primary" type="submit">SEND TO REVIEW</button></div>
      </form>
    </div>
  );
}

function QueueScreen({
  title,
  emptyTitle,
  emptyCopy,
  items,
  customers,
  actionLabel,
  onAction,
  onEdit,
}: {
  title: string;
  emptyTitle: string;
  emptyCopy: string;
  items: ContentItem[];
  customers: Customer[];
  actionLabel: string;
  onAction: (id: string) => void;
  onEdit: (id: string) => void;
}) {
  return (
    <div className="fsp-stack">
      <section className="fsp-page-heading"><p className="fsp-kicker">Human controlled</p><h1>{title}</h1><p>Review the exact current version before approving it.</p></section>
      {!items.length ? <section className="fsp-card fsp-empty"><h2>{emptyTitle}</h2><p>{emptyCopy}</p></section> : items.map((item) => <ContentCard key={item.id} item={item} customer={customerName(customers, item.customerId)} onEdit={() => onEdit(item.id)} action={<button className="fsp-button fsp-button--primary" type="button" onClick={() => onAction(item.id)}>{actionLabel}</button>} />)}
    </div>
  );
}

function ReadyScreen({ items, customers, onEdit }: { items: ContentItem[]; customers: Customer[]; onEdit: (id: string) => void }) {
  return (
    <div className="fsp-stack">
      <section className="fsp-page-heading"><p className="fsp-kicker">Approved queue</p><h1>Ready to Publish</h1><p>Approved content waits here. External publishing remains disabled in Founder Studio Preview.</p></section>
      <div className="fsp-provider-warning fsp-provider-warning--safe"><strong>PUBLISHING DISABLED</strong><span>No TikTok, Instagram or YouTube API will be called from this preview.</span></div>
      {!items.length ? <section className="fsp-card fsp-empty"><h2>No approved content yet</h2><p>Approve an item in Human Review and it will appear here.</p></section> : items.map((item) => <ContentCard key={item.id} item={item} customer={customerName(customers, item.customerId)} onEdit={() => onEdit(item.id)} action={<span className="fsp-ready-badge">READY · NOT PUBLISHED</span>} />)}
    </div>
  );
}

function ContentCard({ item, customer, onEdit, action }: { item: ContentItem; customer: string; onEdit: () => void; action: React.ReactNode }) {
  return (
    <article className="fsp-card fsp-content-card">
      <header><div><span className="fsp-chip">{item.platform}</span><span className="fsp-chip">v{item.version}</span></div><time>{new Date(item.updatedAt).toLocaleString()}</time></header>
      <p className="fsp-content-card__customer">{customer}</p>
      <h2>{item.idea}</h2>
      <section><strong>Hook</strong><p>{item.hook}</p></section>
      <section><strong>Content</strong><p>{item.body}</p></section>
      <section><strong>CTA</strong><p>{item.cta}</p></section>
      <footer><button className="fsp-button" type="button" onClick={onEdit}>EDIT</button>{action}</footer>
    </article>
  );
}
