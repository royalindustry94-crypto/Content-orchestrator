import { useState } from "react";
import { BusinessManagerMark } from "./BusinessManagerMark";
import "./creativeTemplate.css";

type Screen = "dashboard" | "stats" | "transfer" | "planning" | "history" | "info";

const DOCK: Array<{ id: Screen; label: string; icon: string }> = [
  { id: "dashboard", label: "Dashboard", icon: "▦" },
  { id: "stats", label: "Stats", icon: "▮" },
  { id: "transfer", label: "Transfer", icon: "⇄" },
  { id: "planning", label: "Planning", icon: "▦" },
  { id: "history", label: "History", icon: "↺" },
  { id: "info", label: "Info", icon: "i" },
];

function Wave({ tone, uid }: { tone: "hot" | "cyan"; uid: string }) {
  const stroke = tone === "cyan" ? "#00D9FF" : "#FF4D8D";
  const id = `tpl-wave-${tone}-${uid}`;
  return (
    <svg className="tpl-wave" viewBox="0 0 320 110" aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.55" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d="M0 72 C 32 44, 64 96, 96 68 S 160 28, 192 62 256 108, 288 70 320 42, 320 42 V 110 H 0 Z" fill={`url(#${id})`} />
      <path d="M0 72 C 32 44, 64 96, 96 68 S 160 28, 192 62 256 108, 288 70 320 42, 320 42" fill="none" stroke={stroke} strokeWidth="2.6" />
    </svg>
  );
}

function Donut({
  label,
  tone,
}: {
  label: string;
  tone: "hot" | "cyan" | "lime" | "violet";
}) {
  return (
    <article className={`tpl-donut tpl-donut--${tone}`}>
      <span>{label}</span>
      <strong>—</strong>
    </article>
  );
}

function ScreenBody({ screen, uid }: { screen: Screen; uid: string }) {
  if (screen === "dashboard") {
    return (
      <>
        <header className="tpl-profile">
          <span className="tpl-avatar">F</span>
          <div>
            <p>Founder</p>
            <strong>The Business Manager</strong>
          </div>
          <small>TEMPLATE</small>
        </header>
        <section className="tpl-card">
          <p className="tpl-kicker">Statistic graph</p>
          <Wave tone="hot" uid={uid} />
        </section>
        <div className="tpl-donut-row">
          <Donut label="01" tone="hot" />
          <Donut label="02" tone="cyan" />
          <Donut label="03" tone="lime" />
          <Donut label="04" tone="violet" />
        </div>
      </>
    );
  }
  if (screen === "stats") {
    return (
      <>
        <p className="tpl-kicker">General stats</p>
        <div className="tpl-ring" aria-label="Template sample ring">
          <strong>55%</strong>
          <small>Template sample</small>
        </div>
        <ul className="tpl-stat-list">
          {[110, 136, 148].map((value) => (
            <li key={value}>
              <span>General stats</span>
              <b>{value}</b>
              <i style={{ width: `${Math.min(100, value / 1.6)}%` }} />
            </li>
          ))}
        </ul>
        <div className="tpl-bars" aria-hidden="true">
          {[40, 70, 55, 90, 48, 76, 62].map((height, index) => (
            <span key={index} style={{ height: `${height}%` }} />
          ))}
        </div>
      </>
    );
  }
  if (screen === "transfer") {
    return (
      <>
        <p className="tpl-kicker">Balance</p>
        <h2 className="tpl-balance">$1,490.00</h2>
        <p className="tpl-delta">Template sample · +3.44%</p>
        <section className="tpl-card tpl-card--split">
          <Wave tone="cyan" uid={uid} />
          <div className="tpl-mini-bars" aria-hidden="true">
            {[30, 55, 42, 70, 38].map((height, index) => (
              <span key={index} style={{ height: `${height}%` }} />
            ))}
          </div>
        </section>
        <div className="tpl-pie" aria-hidden="true" />
      </>
    );
  }
  if (screen === "planning") {
    return (
      <>
        <p className="tpl-kicker">July</p>
        <div className="tpl-calendar">
          {["S", "M", "T", "W", "T", "F", "S"].map((day, index) => (
            <span className="tpl-calendar__head" key={`${day}-${index}`}>{day}</span>
          ))}
          {Array.from({ length: 31 }, (_, index) => (
            <span className={index === 15 ? "tpl-calendar__day tpl-calendar__day--hot" : "tpl-calendar__day"} key={index}>
              {index + 1}
            </span>
          ))}
        </div>
        <ol className="tpl-agenda">
          <li><time>09:00</time><span>Human Review desk</span></li>
          <li><time>13:30</time><span>Spend cap check</span></li>
          <li><time>16:00</time><span>Workspace stand-up</span></li>
        </ol>
      </>
    );
  }
  if (screen === "history") {
    return (
      <>
        <label className="tpl-search">
          <span className="visually-hidden">Search template rows</span>
          <input placeholder="Search" readOnly />
        </label>
        <p className="tpl-kicker">Send to friends</p>
        <ul className="tpl-tx">
          {[
            ["Alex Rivera", "$8.55"],
            ["Jordan Blake", "$12.00"],
            ["Sam Chen", "$4.20"],
            ["Riley Ng", "$19.80"],
          ].map(([name, amount]) => (
            <li key={name}>
              <span className="tpl-avatar tpl-avatar--sm">{name.slice(0, 1)}</span>
              <div><strong>{name}</strong><small>Template sample</small></div>
              <b>{amount}</b>
            </li>
          ))}
        </ul>
      </>
    );
  }
  return (
    <section className="tpl-info">
      <BusinessManagerMark className="tpl-info__mark" />
      <h2>Visual template</h2>
      <p>Original recreation of the dark neon dashboard language. Sample figures are decorative chrome, not workspace money.</p>
      <ul>
        <li>Human Review Gate still blocks publish.</li>
        <li>Spend caps stay fail-closed.</li>
        <li>No Adobe Stock file is embedded.</li>
      </ul>
    </section>
  );
}

function Phone({
  screen,
  interactive,
  onScreen,
}: {
  screen: Screen;
  interactive?: boolean;
  onScreen?: (next: Screen) => void;
}) {
  return (
    <article className={interactive ? "tpl-phone tpl-phone--live" : "tpl-phone"}>
      <div className="tpl-phone__notch" />
      <div className="tpl-phone__body">
        <ScreenBody screen={screen} uid={interactive ? "live" : screen} />
      </div>
      <nav aria-label={interactive ? "Template screens" : undefined} className="tpl-dock">
        {DOCK.map((item) => (
          <button
            aria-current={screen === item.id ? "page" : undefined}
            className={screen === item.id ? "is-active" : undefined}
            disabled={!interactive}
            key={item.id}
            onClick={() => onScreen?.(item.id)}
            type="button"
          >
            <b>{item.icon}</b>
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
    </article>
  );
}

export default function CreativeTemplate({ onClose }: { onClose: () => void }) {
  const [screen, setScreen] = useState<Screen>("dashboard");
  return (
    <main className="tpl-shell" aria-labelledby="tpl-title">
      <header className="tpl-hero">
        <p className="tpl-kicker">The Business Manager</p>
        <h1 id="tpl-title">Neon dashboard template</h1>
        <p>Charcoal ground, magenta-to-orange actions, cyan charts. Original CSS — not a purchased stock file.</p>
        <button className="button button--primary" onClick={onClose} type="button">Back to sign in</button>
      </header>
      <section className="tpl-live" aria-label="Interactive template">
        <Phone interactive onScreen={setScreen} screen={screen} />
      </section>
      <section className="tpl-gallery" aria-label="Template screen set">
        {(["dashboard", "stats", "transfer", "planning", "history"] as const).map((id) => (
          <Phone key={id} screen={id} />
        ))}
      </section>
    </main>
  );
}
