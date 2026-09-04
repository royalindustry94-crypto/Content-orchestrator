export type ThemeName = "light" | "dark";

export const THEME_STORAGE_KEY = "lumora.theme";

export function readStoredTheme(): ThemeName {
  try {
    const value = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (value === "dark" || value === "light") {
      return value;
    }
  } catch {
    // Private mode or blocked storage must not crash boot.
  }
  return "light";
}

export function applyTheme(theme: ThemeName): void {
  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
  root.dataset.theme = theme;
  root.style.colorScheme = theme;
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) {
    meta.setAttribute("content", theme === "dark" ? "#252525" : "#ffffff");
  }
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Ignore persistence failures; the in-memory class still applies.
  }
}

export function toggleTheme(current: ThemeName): ThemeName {
  const next: ThemeName = current === "light" ? "dark" : "light";
  applyTheme(next);
  return next;
}
