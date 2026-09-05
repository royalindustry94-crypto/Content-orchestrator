// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { BankrollQuad, NeonCapMeter, UnconnectedWaveChart } from "./CreativeVisuals";

afterEach(() => {
  cleanup();
});

describe("Creative workspace visuals", () => {
  it("renders an empty wave shell without inventing currency values", () => {
    render(<UnconnectedWaveChart />);
    expect(screen.getByLabelText(/no connected financial series/i)).toBeDefined();
    expect(screen.queryByText(/\$/)).toBeNull();
  });

  it("refuses to draw a cap meter when no cap is configured", () => {
    render(<NeonCapMeter cap={null} label="Daily cap" remaining={null} />);
    expect(screen.getByText("No cap configured")).toBeDefined();
    expect(screen.queryByText(/% remaining/)).toBeNull();
  });

  it("uses only source-backed remaining/cap values when both exist", () => {
    render(<NeonCapMeter cap="100" label="Daily cap" remaining="40" />);
    expect(screen.getByText("40% remaining")).toBeDefined();
  });

  it("keeps the Home quad disconnected when a time range is selected", () => {
    render(<BankrollQuad />);
    expect(screen.getByText("Revenue")).toBeDefined();
    expect(screen.getByText("Spending")).toBeDefined();
    expect(screen.getByText("Net profit")).toBeDefined();
    expect(screen.getByText("Profit margin")).toBeDefined();
    expect(screen.getAllByText("Not connected").length).toBe(4);
    expect(screen.getAllByText("Source-backed data required").length).toBe(4);
    expect(screen.getAllByRole("button", { name: "Revenue 30D" }).length).toBe(1);
    fireEvent.click(screen.getByRole("button", { name: "Revenue 7D" }));
    expect(screen.getByRole("button", { name: "Revenue 7D" }).getAttribute("aria-pressed")).toBe("true");
    expect(screen.getAllByText("Not connected").length).toBe(4);
    expect(screen.queryByText(/\$/)).toBeNull();
    expect(screen.queryByText(/%/)).toBeNull();
    const markup = document.body.innerHTML;
    expect(markup).toContain("#FF007A");
    expect(markup).toContain("#FF9A00");
    expect(markup).toContain("#FF3358");
  });
});
