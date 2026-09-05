import { useState } from "react";
import { BusinessManagerMark } from "./BusinessManagerMark";
import "./creativeTemplate.css";

type Screen = "dashboard" | "stats" | "transfer" | "planning" | "history" | "info";

const PALETTE = [
  { name: "Charcoal", hex: "#121212" },
  { name: "Panel", hex: "#1C1C21" },
  { name: "Magenta", hex: "#FF007A" },
  { name: "Orange", hex: "#FF9A00" },
  { name: "Cyan", hex: "#00D9FF" },
  { name: "Lime", hex: "#B8F54A" },
];

const DOCK: Array<{ id: Screen; label: string }> = [
  { id: "dashboard", label: "Dashboard" },
  { id: "stats", label: "Stats" },
  { id: "transfer", label: "Transfer" },
  { id: "planning", label: "Planning" },
  { id: "history", label: "History" },
  { id: "info", label: "Info" },
];

const FRIENDS = [
  { name: "Alex Rivera", amount: "$8.55", tone: "hot" },
  { name: "Jordan Blake", amount: "$12.00", tone: "cyan" },
  { name: "Sam Chen", amount: "$4.20", tone: "lime" },
  { name: "Riley Ng", amount: "$19.80", tone: "orange" },
] as const;

const JULY_LEAD_EMPTY = 3;

function DockIcon({ id, active }: { id: Screen; active: boolean }) {
  const stroke = active ? "#FF007A" : "#8B91A0";
  if (id === "dashboard") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="3" y="3" width="8" height="8" rx="1.6" fill="none" stroke={stroke} strokeWidth="1.8" />
        <rect x="13" y="3" width="8" height="8" rx="1.6" fill="none" stroke={stroke} strokeWidth="1.8" />
        <rect x="3" y="13" width="8" height="8" rx="1.6" fill="none" stroke={stroke} strokeWidth="1.8" />
        <rect x="13" y="13" width="8" height="8" rx="1.6" fill="none" stroke={stroke} strokeWidth="1.8" />
      </svg>
    );
  }
  if (id === "stats") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M5 18V10M12 18V6M19 18v-7" fill="none" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    );
  }
  if (id === "transfer") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 8h14l-3-3M20 16H6l3 3" fill="none" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (id === "planning") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="4" y="5" width="16" height="15" rx="2" fill="none" stroke={stroke} strokeWidth="1.8" />
        <path d="M8 3v4M16 3v4M4 10h16" fill="none" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    );
  }
  if (id === "history") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 7v5l3 2" fill="none" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" />
        <circle cx="12" cy="12" r="8" fill="none" stroke={stroke} strokeWidth="1.8" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="8" fill="none" stroke={stroke} strokeWidth="1.8" />
      <path d="M12 11v5M12 8h.01" fill="none" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" />
    </svg>
  );
}

function StatusBar() {
  return (
    <div className="tpl-status" aria-hidden="true">
      <span>9:41</span>
      <span className="tpl-status__icons">
        <b />
        <b />
        <i />
      </span>
    </div>
  );
}

function Wave({ tone, uid }: { tone: "hot" | "cyan"; uid: string }) {
  const stroke = tone === "cyan" ? "#00D9FF" : "#FF007A";
  const mid = tone === "cyan" ? "#00D9FF" : "#FF9A00";
  const id = `tpl-wave-${tone}-${uid}`;
  return (
    <svg className="tpl-wave" viewBox="0 0 320 110" aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.62" />
          <stop offset="55%" stopColor={mid} stopOpacity="0.18" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
        <filter id={`${id}-glow`} x="-20%" y="-40%" width="140%" height="180%">
          <feGaussianBlur stdDeviation="2.4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <path
        d="M0 74 C 28 46, 52 98, 88 70 S 148 24, 186 58 244 108, 278 72 320 40, 320 40 V 110 H 0 Z"
        fill={`url(#${id})`}
      />
      <path
        d="M0 74 C 28 46, 52 98, 88 70 S 148 24, 186 58 244 108, 278 72 320 40, 320 40"
        fill="none"
        filter={`url(#${id}-glow)`}
        stroke={stroke}
        strokeWidth="2.8"
      />
    </svg>
  );
}

function Donut({
  label,
  tone,
  value,
}: {
  label: string;
  tone: "hot" | "cyan" | "lime" | "violet";
  value: number;
}) {
  const colors = {
    hot: "#FF007A",
    cyan: "#00D9FF",
    lime: "#B8F54A",
    violet: "#C084FC",
  };
  const circumference = 2 * Math.PI * 16;
  const dash = (value / 100) * circumference;
  return (
    <article className={`tpl-donut tpl-donut--${tone}`}>
      <span>{label}</span>
      <svg viewBox="0 0 44 44" aria-hidden="true">
        <circle cx="22" cy="22" r="16" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="5" />
        <circle
          cx="22"
          cy="22"
          r="16"
          fill="none"
          stroke={colors[tone]}
          strokeDasharray={`${dash} ${circumference}`}
          strokeLinecap="round"
          strokeWidth="5"
          transform="rotate(-90 22 22)"
        />
      </svg>
    </article>
  );
}

function SampleRing({ uid }: { uid: string }) {
  const gradId = `tpl-ring-grad-${uid}`;
  return (
    <div className="tpl-ring" aria-label="Template sample ring 55 percent">
      <svg viewBox="0 0 160 160" aria-hidden="true">
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#FF007A" />
            <stop offset="48%" stopColor="#00D9FF" />
            <stop offset="100%" stopColor="#FF9A00" />
          </linearGradient>
        </defs>
        <circle cx="80" cy="80" r="62" fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="14" />
        <circle
          cx="80"
          cy="80"
          r="62"
          fill="none"
          stroke={`url(#${gradId})`}
          strokeDasharray={`${2 * Math.PI * 62 * 0.55} ${2 * Math.PI * 62}`}
          strokeLinecap="round"
          strokeWidth="14"
          transform="rotate(-90 80 80)"
        />
      </svg>
      <div>
        <strong>55%</strong>
        <small>Template sample</small>
      </div>
    </div>
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
          <Donut label="01" tone="hot" value={72} />
          <Donut label="02" tone="cyan" value={54} />
          <Donut label="03" tone="lime" value={81} />
          <Donut label="04" tone="violet" value={46} />
        </div>
      </>
    );
  }
  if (screen === "stats") {
    return (
      <>
        <p className="tpl-kicker">General stats</p>
        <SampleRing uid={uid} />
        <ul className="tpl-stat-list">
          {[
            { value: 110, width: 68 },
            { value: 136, width: 84 },
            { value: 148, width: 92 },
          ].map((row) => (
            <li key={row.value}>
              <span>General stats</span>
              <b>{row.value}</b>
              <i style={{ width: `${row.width}%` }} />
            </li>
          ))}
        </ul>
        <div className="tpl-bars" aria-hidden="true">
          {[42, 70, 55, 92, 48, 76, 64].map((height, index) => (
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
            {[32, 58, 44, 76, 40].map((height, index) => (
              <span key={index} style={{ height: `${height}%` }} />
            ))}
          </div>
        </section>
        <div className="tpl-pie-wrap">
          <div className="tpl-pie" aria-hidden="true" />
          <ul className="tpl-legend">
            <li><i className="tpl-swatch tpl-swatch--hot" /> Magenta</li>
            <li><i className="tpl-swatch tpl-swatch--orange" /> Orange</li>
            <li><i className="tpl-swatch tpl-swatch--cyan" /> Cyan</li>
            <li><i className="tpl-swatch tpl-swatch--violet" /> Violet</li>
          </ul>
        </div>
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
          {Array.from({ length: JULY_LEAD_EMPTY }, (_, index) => (
            <span className="tpl-calendar__day tpl-calendar__day--empty" key={`empty-${index}`} />
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
          {FRIENDS.map((friend) => (
            <li key={friend.name}>
              <span className={`tpl-avatar tpl-avatar--sm tpl-avatar--${friend.tone}`}>{friend.name.slice(0, 1)}</span>
              <div>
                <strong>{friend.name}</strong>
                <small>Template sample</small>
              </div>
              <b>{friend.amount}</b>
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
      <div className="tpl-phone__bezel">
        <div className="tpl-phone__notch" />
        <StatusBar />
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
              <DockIcon active={screen === item.id} id={item.id} />
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="tpl-home-indicator" aria-hidden="true" />
      </div>
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
        <p>Original five-screen kit in the same charcoal, magenta, orange, cyan, and lime language. Decorative sample figures never write to Home Bankroll.</p>
        <ul className="tpl-palette" aria-label="Template colours">
          {PALETTE.map((swatch) => (
            <li key={swatch.hex}>
              <i style={{ background: swatch.hex }} />
              <span>{swatch.name}</span>
              <small>{swatch.hex}</small>
            </li>
          ))}
        </ul>
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
