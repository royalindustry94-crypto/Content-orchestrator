// @vitest-environment jsdom
import { afterEach, describe, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import ThemeToggle from "./ThemeToggle";
import { THEME_STORAGE_KEY } from "./theme";

afterEach(() => {
  cleanup();
  document.documentElement.classList.remove("dark");
  window.localStorage.removeItem(THEME_STORAGE_KEY);
});

describe("ThemeToggle", () => {
  it("starts in light mode and switches the document to dark", () => {
    render(<ThemeToggle />);
    const button = screen.getByRole("button", { name: /switch to dark theme/i });
    fireEvent.click(button);
    expect(document.documentElement.classList.contains("dark")).toBe(true);
    expect(screen.getByRole("button", { name: /switch to light theme/i })).toBeDefined();
  });
});
