// @vitest-environment jsdom
import { afterEach, describe, expect, it } from "vitest";

import {
  THEME_STORAGE_KEY,
  applyTheme,
  readStoredTheme,
  toggleTheme,
} from "./theme";

afterEach(() => {
  document.documentElement.classList.remove("dark");
  delete document.documentElement.dataset.theme;
  document.documentElement.style.colorScheme = "";
  window.localStorage.removeItem(THEME_STORAGE_KEY);
});

describe("theme", () => {
  it("defaults to the official FastAPI template light theme", () => {
    expect(readStoredTheme()).toBe("light");
  });

  it("applies and persists a dark theme on the document root", () => {
    applyTheme("dark");
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(document.documentElement.style.colorScheme).toBe("dark");
    expect(window.localStorage.getItem(THEME_STORAGE_KEY)).toBe("dark");
    expect(readStoredTheme()).toBe("dark");
  });

  it("toggles light to dark and back", () => {
    expect(toggleTheme("light")).toBe("dark");
    expect(toggleTheme("dark")).toBe("light");
    expect(document.documentElement.classList.contains("dark")).toBe(false);
  });
});
