type BusinessManagerMarkProps = {
  className?: string;
  title?: string;
};

/**
 * Compact, accessible TB monogram based on the approved Business Manager
 * direction: paired T/B letterforms, rising bars, and an upward trajectory.
 */
export function BusinessManagerMark({
  className = "",
  title = "The Business Manager",
}: BusinessManagerMarkProps) {
  return (
    <svg
      className={`business-manager-mark ${className}`.trim()}
      viewBox="0 0 96 96"
      role="img"
      aria-label={title}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <linearGradient id="tb-gold" x1="12" y1="10" x2="78" y2="86" gradientUnits="userSpaceOnUse">
          <stop stopColor="#E2C45A" />
          <stop offset="0.52" stopColor="#D4AF37" />
          <stop offset="1" stopColor="#A97714" />
        </linearGradient>
      </defs>
      <rect x="2" y="2" width="92" height="92" rx="22" fill="#0A0D12" stroke="#D4AF37" strokeOpacity="0.45" />
      <path d="M16 20h42v12H43v39H30V32H16V20Z" fill="url(#tb-gold)" />
      <path d="M46 20h17c13 0 22 7 22 17 0 7-4 12-10 14 8 2 13 8 13 17 0 12-10 20-25 20H46V76h15c8 0 13-3 13-9 0-6-5-9-13-9H46V46h13c7 0 11-3 11-8s-4-7-11-7H46V20Z" fill="url(#tb-gold)" />
      <path d="M15 77h8v8h-8v-8Zm12-10h8v18h-8V67Zm12-12h8v30h-8V55Zm12-12h8v42h-8V43Z" fill="url(#tb-gold)" opacity="0.96" />
      <path d="M13 69c13-2 22-8 30-18 9-12 18-20 35-27" fill="none" stroke="#F6D56B" strokeLinecap="round" strokeWidth="5" />
      <path d="m69 20 11 2-4 10" fill="none" stroke="#F6D56B" strokeLinecap="round" strokeLinejoin="round" strokeWidth="5" />
    </svg>
  );
}
