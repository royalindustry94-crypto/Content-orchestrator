// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { NeonCapMeter, UnconnectedWaveChart } from "./CreativeVisuals";

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
});
