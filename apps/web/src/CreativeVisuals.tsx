/**
 * Original decorative shells for The Business Manager creative workspace theme.
 * These SVGs are authored in-repo. They do not embed Adobe Stock #235999682
 * or any purchased template asset. They never invent financial values.
 */

import { useId } from "react";

type WaveTone = "hot" | "cyan";

export function UnconnectedWaveChart({
  tone = "hot",
  label = "Visualization shell — no connected financial series",
}: {
  tone?: WaveTone;
  label?: string;
}) {
  const gradientId = `cw-wave-${tone}-${useId().replaceAll(":", "")}`;
  const stroke = tone === "cyan" ? "#2DE2E6" : "#B8F54A";
  return (
    <figure className={`creative-wave creative-wave--${tone}`} aria-label={label}>
      <svg viewBox="0 0 360 120" role="img" aria-hidden="true">
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={stroke} stopOpacity="0.42" />
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
          strokeWidth="2.4"
          strokeLinecap="round"
        />
      </svg>
      <figcaption>{label}</figcaption>
    </figure>
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
