import {
  useEffect,
  useRef,
  useState,
  type FormEvent,
  type ReactNode,
} from "react";
import {
  askMissionAssistant,
  getLiveLogs,
  globalSearch,
  postMissionAction,
  type ActivityFeed,
  type AssistantAnswer,
  type ExecutiveMode,
  type GlobalSearch,
  type LiveLogs,
  type QuickActionResult,
} from "./api";

function money(value: string): string {
  return new Intl.NumberFormat(undefined, {
    style: "currency",
    currency: "USD",
  }).format(Number(value));
}

function date(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "short",
    timeStyle: "medium",
  }).format(new Date(value));
}

function Card({
  label,
  value,
  detail,
}: {
  label: string;
  value: ReactNode;
  detail?: string;
}) {
  return (
    <article className="metric">
      <p>{label}</p>
      <strong>{value}</strong>
      {detail ? <span>{detail}</span> : null}
    </article>
  );
}

export function GlobalSearchBar({
  token,
  workspaceId,
  onOpen,
}: {
  token: string;
  workspaceId: string;
  onOpen: (type: string) => void;
}) {
  const [query, setQuery] = useState("");
  const [data, setData] = useState<GlobalSearch | null>(null);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const focus = () => inputRef.current?.focus();
    window.addEventListener("mission-search-focus", focus);
    return () => window.removeEventListener("mission-search-focus", focus);
  }, []);

  useEffect(() => {
    if (query.trim().length < 2) {
      setData(null);
      return;
    }
    const timer = window.setTimeout(() => {
      void globalSearch(token, workspaceId, query)
        .then(setData)
        .catch((err: unknown) =>
          setError(err instanceof Error ? err.message : "Search failed"),
        );
    }, 250);
    return () => window.clearTimeout(timer);
  }, [query, token, workspaceId]);

  return (
    <div className="global-search">
      <input
        ref={inputRef}
        value={query}
        onChange={(event) => {
          setQuery(event.target.value);
          setError(null);
        }}
        placeholder="Search customers, leads, pipelines, workers, jobs, content, reviews, videos, GitHub, logs"
        aria-label="Global search"
      />
      <kbd>⌘K</kbd>
      {error ? <div className="search-results search-results--error">{error}</div> : null}
      {data ? (
        <div className="search-results">
          <p>{data.total} result(s)</p>
          {data.results.length === 0 ? (
            <span>No live records matched.</span>
          ) : (
            data.results.map((result) => (
              <button
                type="button"
                key={`${result.type}:${result.id}`}
                onClick={() => {
                  if (result.url) {
                    window.open(result.url, "_blank", "noopener,noreferrer");
                  } else {
                    onOpen(result.type);
                  }
                  setQuery("");
                  setData(null);
                }}
              >
                <span className="search-type">{result.type}</span>
                <strong>{result.title}</strong>
                <small>{result.subtitle ?? result.status ?? result.id}</small>
              </button>
            ))
          )}
        </div>
      ) : null}
    </div>
  );
}

type Navigate = (screen: string) => void;

export function CommandPalette({
  token,
  workspaceId,
  navigate,
}: {
  token: string;
  workspaceId: string;
  navigate: Navigate;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<QuickActionResult | null>(null);

  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setOpen((value) => !value);
      }
      if (event.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", listener);
    return () => window.removeEventListener("keydown", listener);
  }, []);

  const commands = [
    { label: "Create workspace", run: () => navigate("actions") },
    { label: "Create pipeline", run: () => navigate("actions") },
    {
      label: "Retry job",
      run: () =>
        postMissionAction(token, workspaceId, "retry-failed-jobs").then(setResult),
    },
    {
      label: "Pause workers",
      run: () =>
        postMissionAction(token, workspaceId, "pause-workers").then(setResult),
    },
    {
      label: "Resume workers",
      run: () =>
        postMissionAction(token, workspaceId, "resume-workers").then(setResult),
    },
    {
      label: "Search customer",
      run: () => window.dispatchEvent(new Event("mission-search-focus")),
    },
    { label: "Open worker", run: () => navigate("worker-timeline") },
    { label: "Open logs", run: () => navigate("logs") },
  ];
  const visible = commands.filter((command) =>
    command.label.toLowerCase().includes(query.toLowerCase()),
  );

  if (!open) return null;
  return (
    <div className="command-backdrop" onClick={() => setOpen(false)}>
      <section
        className="command-palette"
        role="dialog"
        aria-modal="true"
        aria-label="Command palette"
        onClick={(event) => event.stopPropagation()}
      >
        <input
          autoFocus
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Type a command"
        />
        {visible.map((command) => (
          <button
            type="button"
            key={command.label}
            onClick={() => {
              void Promise.resolve(command.run()).finally(() => setOpen(false));
            }}
          >
            {command.label}
          </button>
        ))}
        {result ? <p>{result.message}</p> : null}
      </section>
    </div>
  );
}

export function UniversalTimelineView({ data }: { data: ActivityFeed }) {
  if (data.items.length === 0) {
    return <div className="empty">No timeline events recorded.</div>;
  }
  return (
    <div className="universal-timeline">
      {data.items.map((item) => (
        <article key={item.id}>
          <i className={`timeline-dot timeline-dot--${item.severity}`} />
          <div>
            <strong>{item.title}</strong>
            <p>{item.detail ?? item.kind}</p>
            <small>{date(item.occurred_at)} · {item.source}</small>
          </div>
        </article>
      ))}
    </div>
  );
}

export function ExecutiveModeView({ data }: { data: ExecutiveMode }) {
  const overall = data.health.some((item) => item.status === "red")
    ? "Red"
    : data.health.some((item) => item.status === "amber")
      ? "Amber"
      : "Green";
  return (
    <div className="executive-mode">
      <div className="executive-grid">
        <Card label="Health" value={overall} detail={data.health.map((h) => `${h.label}: ${h.status}`).join(" · ")} />
        <Card label="Revenue MTD" value={money(data.revenue_mtd_usd)} />
        <Card label="Spend Today" value={money(data.spend_today_usd)} detail={`Month ${money(data.spend_month_usd)}`} />
        <Card label="Workers" value={`${data.workers_online}/${data.workers_total}`} detail="Online / total" />
        <Card label="Jobs" value={data.jobs_running} detail={`${data.jobs_waiting} waiting · ${data.jobs_failed_today} failed today`} />
        <Card label="Critical Alerts" value={data.critical_alerts} />
        <Card label="Reviews Waiting" value={data.reviews_waiting} />
        <Card label="New Customers" value={data.new_customers_today} detail="Today" />
      </div>
      <section className="executive-summary">
        <h3>Today&apos;s summary</h3>
        <ul>{data.todays_summary.map((item) => <li key={item}>{item}</li>)}</ul>
      </section>
    </div>
  );
}

export function LiveLogsView({
  token,
  workspaceId,
  initial,
}: {
  token: string;
  workspaceId: string;
  initial: LiveLogs;
}) {
  const [data, setData] = useState(initial);
  const [filters, setFilters] = useState({
    worker_id: "",
    pipeline_id: "",
    job_id: "",
    severity: "",
  });
  const submit = (event: FormEvent) => {
    event.preventDefault();
    void getLiveLogs(token, workspaceId, filters).then(setData);
  };
  return (
    <>
      <form className="ops-toolbar log-filters" onSubmit={submit}>
        <input aria-label="Workspace filter" value={workspaceId} disabled />
        <input placeholder="Worker UUID" value={filters.worker_id} onChange={(e) => setFilters({ ...filters, worker_id: e.target.value })} />
        <input placeholder="Pipeline UUID" value={filters.pipeline_id} onChange={(e) => setFilters({ ...filters, pipeline_id: e.target.value })} />
        <input placeholder="Job UUID" value={filters.job_id} onChange={(e) => setFilters({ ...filters, job_id: e.target.value })} />
        <select value={filters.severity} onChange={(e) => setFilters({ ...filters, severity: e.target.value })}>
          <option value="">All severities</option>
          {["debug", "info", "warning", "error", "critical"].map((value) => <option key={value}>{value}</option>)}
        </select>
        <button type="submit">Filter logs</button>
      </form>
      {data.logs.length === 0 ? (
        <div className="empty">No worker logs match these filters.</div>
      ) : (
        <div className="logs-console">
          {data.logs.map((log) => (
            <article key={log.id} className={`log-line log-line--${log.severity}`}>
              <time>{date(log.occurred_at)}</time>
              <span>{log.severity}</span>
              <strong>{log.worker_name}</strong>
              <code>{log.message}</code>
            </article>
          ))}
        </div>
      )}
    </>
  );
}

export function AssistantPanel({
  token,
  workspaceId,
}: {
  token: string;
  workspaceId: string;
}) {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<AssistantAnswer | null>(null);
  const [busy, setBusy] = useState(false);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    try {
      setAnswer(await askMissionAssistant(token, workspaceId, question));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="assistant-panel">
      <form onSubmit={(event) => void submit(event)}>
        <textarea
          required
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask: What failed today? Why is worker 4 idle? Show today's spend. Show blocked reviews."
        />
        <button type="submit" disabled={busy}>{busy ? "Analyzing…" : "Ask live system"}</button>
      </form>
      {answer ? (
        <section>
          <p className="eyebrow">{answer.intent}</p>
          <h3>{answer.answer}</h3>
          {answer.facts.length ? <pre>{JSON.stringify(answer.facts, null, 2)}</pre> : null}
        </section>
      ) : null}
    </div>
  );
}
