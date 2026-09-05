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
    expect(screen.getByLabelText("Template colours")).toBeDefined();
    expect(screen.getAllByText("#FF007A").length).toBeGreaterThan(0);
  });

  it("switches the live phone to the Info screen from the template dock", () => {
    render(<CreativeTemplate onClose={() => {}} />);
    const dock = screen.getByRole("navigation", { name: "Template screens" });
    fireEvent.click(dock.querySelectorAll("button")[5]);
    expect(screen.getByText("Visual template")).toBeDefined();
    expect(screen.getByText(/Human Review Gate still blocks publish/)).toBeDefined();
  });
});
