// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import CreativeTemplate from "./CreativeTemplate";

afterEach(() => {
  cleanup();
});

describe("neon dashboard template", () => {
  it("renders the five mood-board screens without treating sample money as workspace data", () => {
    render(<CreativeTemplate onClose={() => {}} />);
    expect(screen.getByRole("heading", { name: "Neon dashboard template" })).toBeDefined();
    expect(screen.getAllByText("The Business Manager").length).toBeGreaterThan(0);
    expect(screen.getAllByText("TEMPLATE").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Template sample").length).toBeGreaterThan(0);
    expect(screen.getAllByText("$1,490.00").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Send to friends").length).toBeGreaterThan(0);
    expect(screen.getAllByText("July").length).toBeGreaterThan(0);
  });

  it("opens the About notes without exposing an Info dock tab", () => {
    render(<CreativeTemplate onClose={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "About this template" }));
    expect(screen.getByText("Visual template")).toBeDefined();
    expect(screen.getByText(/Human Review Gate still blocks publish/)).toBeDefined();
  });
});
