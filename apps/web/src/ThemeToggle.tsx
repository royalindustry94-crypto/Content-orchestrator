import { useState } from "react";

import { applyTheme, readStoredTheme, toggleTheme, type ThemeName } from "./theme";

type Props = {
  className?: string;
};

export default function ThemeToggle({ className = "" }: Props) {
  const [theme, setTheme] = useState<ThemeName>(() => {
    const initial = readStoredTheme();
    applyTheme(initial);
    return initial;
  });

  const nextLabel = theme === "light" ? "Switch to dark theme" : "Switch to light theme";

  return (
    <button
      aria-label={nextLabel}
      className={`icon-button theme-toggle ${className}`.trim()}
      onClick={() => setTheme((current) => toggleTheme(current))}
      title={nextLabel}
      type="button"
    >
      {theme === "light" ? (
        <svg aria-hidden="true" className="ui-icon" fill="none" height="18" viewBox="0 0 24 24" width="18" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8">
          <path d="M21 14.5A8.5 8.5 0 1 1 9.5 3 7 7 0 0 0 21 14.5z" />
        </svg>
      ) : (
        <svg aria-hidden="true" className="ui-icon" fill="none" height="18" viewBox="0 0 24 24" width="18" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.8">
          <circle cx="12" cy="12" r="4" />
          <path d="M12 3v2M12 19v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M3 12h2M19 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4" />
        </svg>
      )}
    </button>
  );
}
