type BusinessManagerMarkProps = {
  className?: string;
  title?: string;
};

/**
 * Approved compact Business Manager mark: a silver upward geometric chevron
 * surrounding a gold inner chevron. The full lockup is used on auth surfaces.
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
        <linearGradient id="bm-silver" x1="22" y1="12" x2="70" y2="82" gradientUnits="userSpaceOnUse">
          <stop stopColor="#FFFFFF" />
          <stop offset="0.46" stopColor="#E5E7EB" />
          <stop offset="1" stopColor="#9CA3AF" />
        </linearGradient>
        <linearGradient id="bm-gold" x1="22" y1="70" x2="76" y2="50" gradientUnits="userSpaceOnUse">
          <stop stopColor="#8E6213" />
          <stop offset="0.42" stopColor="#E2C45A" />
          <stop offset="0.7" stopColor="#D4AF37" />
          <stop offset="1" stopColor="#9C6A13" />
        </linearGradient>
      </defs>
      <path d="M48 8 13 76l35-29 35 29L48 8Zm0 13 21 41-21-18-21 18 21-41Z" fill="url(#bm-silver)" />
      <path d="m48 50-27 25 27-11 27 11-27-25Zm0 8 12 12-12-5-12 5 12-12Z" fill="url(#bm-gold)" />
    </svg>
  );
}
