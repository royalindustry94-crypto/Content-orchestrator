import { useState } from "react";
import { BusinessManagerMark } from "./BusinessManagerMark";
import "./creativeTemplate.css";

type Screen = "dashboard" | "stats" | "transfer" | "planning" | "history";

const KIT: Screen[] = ["dashboard", "stats", "transfer", "planning", "history"];

const DOCK: Array<{ id: Screen; label: string }> = [
  { id: "dashboard", label: "Dashboard" },
  { id: "stats", label: "Stats" },
  { id: "transfer", label: "Transfer" },
  { id: "planning", label: "Planning" },
  { id: "history", label: "History" },
];

const FRIENDS = [
  { name: "Alex Rivera", amount: "$8.55", face: "one" },
  { name: "Jordan Blake", amount: "$12.00", face: "two" },
  { name: "Sam Chen", amount: "$4.20", face: "three" },
  { name: "Riley Ng", amount: "$19.80", face: "four" },
] as const;

const JULY_LEAD_EMPTY = 3;

function DockIcon({ id, active }: { id: Screen; active: boolean }) {
  const stroke = active ? "#FF007A" : "#7A8190";
  if (id === "dashboard") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="4" y="4" width="7" height="7" rx="1.4" fill="none" stroke={stroke} strokeWidth="1.7" />
        <rect x="13" y="4" width="7" height="7" rx="1.4" fill="none" stroke={stroke} strokeWidth="1.7" />
        <rect x="4" y="13" width="7" height="7" rx="1.4" fill="none" stroke={stroke} strokeWidth="1.7" />
        <rect x="13" y="13" width="7" height="7" rx="1.4" fill="none" stroke={stroke} strokeWidth="1.7" />
      </svg>
    );
  }
  if (id === "stats") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M6 17V9M12 17V6M18 17v-5" fill="none" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" />
      </svg>
    );
  }
  if (id === "transfer") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M5 8h13l-3.2-3M19 16H6l3.2 3" fill="none" stroke={stroke} strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  }
  if (id === "planning") {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <rect x="5" y="6" width="14" height="13" rx="2" fill="none" stroke={stroke} strokeWidth="1.7" />
        <path d="M8 4v4M16 4v4M5 10h14" fill="none" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" />
      </svg>
    );
  }
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="12" r="7.2" fill="none" stroke={stroke} strokeWidth="1.7" />
      <path d="M12 8.2v4.2l2.6 1.6" fill="none" stroke={stroke} strokeWidth="1.7" strokeLinecap="round" />
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
  const accent = tone === "cyan" ? "#B8F54A" : "#FF9A00";
  const id = `tpl-wave-${tone}-${uid}`;
  return (
    <svg className="tpl-wave" viewBox="0 0 320 118" aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.85" />
          <stop offset="42%" stopColor={mid} stopOpacity="0.35" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
        <filter id={`${id}-glow`} x="-30%" y="-60%" width="160%" height="220%">
          <feGaussianBlur stdDeviation="3.2" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <path
        d="M0 78 C 26 50, 48 102, 84 74 S 142 22, 180 56 238 112, 274 76 320 38, 320 38 V 118 H 0 Z"
        fill={`url(#${id})`}
      />
      <path
        d="M0 78 C 26 50, 48 102, 84 74 S 142 22, 180 56 238 112, 274 76 320 38, 320 38"
        fill="none"
        filter={`url(#${id}-glow)`}
        stroke={stroke}
        strokeWidth="3.4"
      />
      <path
        d="M0 86 C 30 62, 58 104, 96 80 S 154 36, 192 64 246 108, 282 84 320 52, 320 52"
        fill="none"
        opacity="0.45"
        stroke={mid}
        strokeWidth="1.4"
      />
      <path
        d="M0 92 C 36 70, 70 108, 108 86 S 168 48, 208 72 258 110, 292 90 320 62, 320 62"
        fill="none"
        opacity="0.35"
        stroke={accent}
        strokeWidth="1.1"
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
  tone: "hot" | "cyan" | "lime" | "orange";
  value: number;
}) {
  const colors = {
    hot: "#FF007A",
    cyan: "#00D9FF",
    lime: "#B8F54A",
    orange: "#FF9A00",
  };
  const circumference = 2 * Math.PI * 15.5;
  const dash = (value / 100) * circumference;
  return (
    <article className={`tpl-donut tpl-donut--${tone}`}>
      <span>{label}</span>
      <svg viewBox="0 0 44 44" aria-hidden="true">
        <circle cx="22" cy="22" r="15.5" fill="none" stroke="rgba(255,255,255,0.07)" strokeWidth="6.2" />
        <circle
          cx="22"
          cy="22"
          r="15.5"
          fill="none"
          stroke={colors[tone]}
          strokeDasharray={`${dash} ${circumference}`}
          strokeLinecap="round"
          strokeWidth="6.2"
          transform="rotate(-90 22 22)"
        />
      </svg>
    </article>
  );
}

function SampleRing({ uid }: { uid: string }) {
  const gradId = `tpl-ring-grad-${uid}`;
  const glowId = `tpl-ring-glow-${uid}`;
  const radius = 58;
  const circ = 2 * Math.PI * radius;
  return (
    <div className="tpl-ring" aria-label="Template sample ring 55 percent">
      <svg viewBox="0 0 160 160" aria-hidden="true">
        <defs>
          <linearGradient id={gradId} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#FF007A" />
            <stop offset="38%" stopColor="#00D9FF" />
            <stop offset="72%" stopColor="#B8F54A" />
            <stop offset="100%" stopColor="#FF9A00" />
          </linearGradient>
          <filter id={glowId} x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="3.6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <circle cx="80" cy="80" r={radius} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="16" />
        <circle
          cx="80"
          cy="80"
          r={radius}
          fill="none"
          filter={`url(#${glowId})`}
          stroke={`url(#${gradId})`}
          strokeDasharray={`${circ * 0.55} ${circ}`}
          strokeLinecap="round"
          strokeWidth="16"
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
          <span className="tpl-face tpl-face--founder" aria-hidden="true" />
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
          <Donut label="01" tone="hot" value={78} />
          <Donut label="02" tone="cyan" value={56} />
          <Donut label="03" tone="lime" value={84} />
          <Donut label="04" tone="orange" value={42} />
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
          {[38, 72, 54, 94, 46, 80, 62].map((height, index) => (
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
            {[30, 62, 44, 80, 38].map((height, index) => (
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
            <li><i className="tpl-swatch tpl-swatch--lime" /> Lime</li>
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
            <span className={`tpl-face tpl-face--${friend.face}`} aria-hidden="true" />
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

function Phone({ screen }: { screen: Screen }) {
  return (
    <article className="tpl-phone">
      <div className="tpl-phone__bezel">
        <div className="tpl-phone__ear" aria-hidden="true" />
        <div className="tpl-phone__notch" />
        <StatusBar />
        <div className="tpl-phone__body">
          <ScreenBody screen={screen} uid={screen} />
        </div>
        <nav className="tpl-dock" aria-hidden="true">
          {DOCK.map((item) => (
            <span className={screen === item.id ? "is-active" : undefined} key={item.id}>
              <DockIcon active={screen === item.id} id={item.id} />
              <b>{item.label}</b>
            </span>
          ))}
        </nav>
        <div className="tpl-home-indicator" aria-hidden="true" />
      </div>
    </article>
  );
}

export default function CreativeTemplate({ onClose }: { onClose: () => void }) {
  const [about, setAbout] = useState(false);
  return (
    <main className="tpl-shell" aria-labelledby="tpl-title">
      <header className="tpl-topbar">
        <button className="tpl-topbar__back" onClick={onClose} type="button">Back to sign in</button>
        <div>
          <p className="tpl-kicker">The Business Manager</p>
          <h1 id="tpl-title">Neon dashboard template</h1>
        </div>
        <button className="tpl-topbar__about" onClick={() => setAbout((open) => !open)} type="button">
          {about ? "Hide info" : "About this template"}
        </button>
      </header>
      {about ? (
        <section className="tpl-about" aria-label="Template notes">
          <BusinessManagerMark className="tpl-info__mark" />
          <h2>Visual template</h2>
          <p>Original recreation of the dark neon dashboard language. Sample figures are decorative chrome, not workspace money.</p>
          <ul>
            <li>Human Review Gate still blocks publish.</li>
            <li>Spend caps stay fail-closed.</li>
            <li>No Adobe Stock file is embedded.</li>
          </ul>
        </section>
      ) : null}
      <section className="tpl-kit" aria-label="Template screen set">
        {KIT.map((id) => (
          <Phone key={id} screen={id} />
        ))}
      </section>
    </main>
  );
}
