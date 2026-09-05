/**
 * Original decorative shells for The Business Manager creative workspace theme.
 * These SVGs are authored in-repo. They do not embed Adobe Stock #235999682
 * or any purchased template asset. They never invent financial values.
 */

import { useId, useState } from "react";

const PERIODS = ["3D", "7D", "30D", "90D", "1Y"] as const;
type Period = (typeof PERIODS)[number];

const BANKROLL_METRICS = [
  { id: "01", label: "Revenue" },
  { id: "02", label: "Spending" },
  { id: "03", label: "Net profit" },
  { id: "04", label: "Profit margin" },
] as const;

const RING_STOPS: Record<(typeof BANKROLL_METRICS)[number]["id"], [string, string]> = {
  "01": ["#FF007A", "#FF9A00"],
  "02": ["#FF9A00", "#FF3358"],
  "03": ["#B8F54A", "#00D9FF"],
  "04": ["#FF007A", "#FF3358"],
};

type WaveTone = "hot" | "cyan";

export function UnconnectedWaveChart({
  tone = "hot",
  label = "Visualization shell — no connected financial series",
}: {
  tone?: WaveTone;
  label?: string;
}) {
  const gradientId = `cw-wave-${tone}-${useId().replaceAll(":", "")}`;
  const stroke = tone === "cyan" ? "#00D9FF" : "#FF007A";
  const accent = tone === "cyan" ? "#B8F54A" : "#FF9A00";
  return (
    <figure className={`creative-wave creative-wave--${tone}`} aria-label={label}>
      <svg viewBox="0 0 360 120" role="img" aria-hidden="true">
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={stroke} stopOpacity="0.2" />
          <stop offset="100%" stopColor={stroke} stopOpacity="0" />
        </linearGradient>
        </defs>
        <path
          d="M0 78 C 36 52, 72 96, 108 70 S 180 40, 216 68 288 110, 324 74 360 48, 360 48 V 120 H 0 Z"
          fill={`url(#${gradientId})`}
        />
        <path
          d="M0 78 C 36 52, 72 96, 108 70 S 180 40, 216 68 288 110, 324 74 360 48, 360 48"
          fill="none"
          stroke={stroke}
          strokeWidth="1.3"
          strokeLinecap="round"
        />
        <path
          d="M0 86 C 40 64, 80 102, 118 78 S 190 50, 228 74 296 108, 332 84 360 58, 360 58"
          fill="none"
          opacity="0.4"
          stroke={accent}
          strokeWidth="0.8"
          strokeLinecap="round"
        />
      </svg>
      <figcaption>{label}</figcaption>
    </figure>
  );
}

function PeriodFilter({
  label,
  value,
  onChange,
}: {
  label: string;
  value: Period;
  onChange: (period: Period) => void;
}) {
  return (
    <div
      className="bankroll-period"
      role="group"
      aria-label={`${label} time range. No connected series for this filter.`}
    >
      {PERIODS.map((period) => (
        <button
          key={period}
          type="button"
          className={period === value ? "bankroll-period__tab is-active" : "bankroll-period__tab"}
          aria-pressed={period === value}
          aria-label={`${label} ${period}`}
          onClick={() => onChange(period)}
        >
          {period}
        </button>
      ))}
    </div>
  );
}

function BankrollShellRing({ tone }: { tone: (typeof BANKROLL_METRICS)[number]["id"] }) {
  const gradientId = `bankroll-ring-${tone}-${useId().replaceAll(":", "")}`;
  const [start, end] = RING_STOPS[tone];
  return (
    <svg className="bankroll-ring" viewBox="0 0 120 120" aria-hidden="true">
      <defs>
        <linearGradient id={gradientId} x1="0.12" y1="0.08" x2="0.92" y2="0.94">
          <stop offset="0%" stopColor={start} />
          <stop offset="100%" stopColor={end} />
        </linearGradient>
      </defs>
      <circle cx="60" cy="60" r="48" fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="12" />
      <circle
        cx="60"
        cy="60"
        r="48"
        fill="none"
        stroke={`url(#${gradientId})`}
        strokeWidth="7.5"
        strokeLinecap="round"
        opacity="0.96"
      />
      <circle cx="60" cy="60" r="41.5" fill="none" stroke="rgba(18,18,18,0.55)" strokeWidth="1.15" />
    </svg>
  );
}

export function BankrollQuad() {
  const [periods, setPeriods] = useState<Record<string, Period>>({
    Revenue: "30D",
    Spending: "30D",
    "Net profit": "30D",
    "Profit margin": "30D",
  });

  return (
    <div className="financial-overview__circle-grid" role="list">
      {BANKROLL_METRICS.map((metric, index) => (
        <article
          key={metric.label}
          role="listitem"
          className={`financial-overview__circle-card financial-overview__circle-card--${metric.id}${index >= 2 ? " is-flipped" : ""}`}
        >
          <span>{metric.label}</span>
          <PeriodFilter
            label={metric.label}
            value={periods[metric.label]}
            onChange={(next) => setPeriods((current) => ({ ...current, [metric.label]: next }))}
          />
          <div className="financial-overview__circle" aria-label={`${metric.label}: financial source not connected`}>
            <BankrollShellRing tone={metric.id} />
            <div className="financial-overview__circle-copy">
              <strong>Not connected</strong>
              <small>Source-backed data required</small>
            </div>
          </div>
        </article>
      ))}
    </div>
  );
}

export function NeonCapMeter({
  label,
  remaining,
  cap,
}: {
  label: string;
  remaining: string | null;
  cap: string | null;
}) {
  const configured = remaining != null && cap != null && Number(cap) > 0;
  const ratio = configured ? Math.max(0, Math.min(1, Number(remaining) / Number(cap))) : 0;
  return (
    <div className="neon-cap">
      <div className="neon-cap__copy">
        <span>{label}</span>
        <strong>{configured ? `${Math.round(ratio * 100)}% remaining` : "No cap configured"}</strong>
      </div>
      <div
        aria-hidden="true"
        className={configured ? "neon-cap__track" : "neon-cap__track neon-cap__track--empty"}
      >
        <i style={configured ? { width: `${Math.round(ratio * 100)}%` } : undefined} />
      </div>
    </div>
  );
}
