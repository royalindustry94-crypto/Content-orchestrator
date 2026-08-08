// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import ErrorBoundary from "./ErrorBoundary";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function RenderFailure({ fail }: { fail: boolean }) {
  if (fail) throw new Error("deliberate render failure");
  return <p>Recovered screen</p>;
}

describe("ErrorBoundary", () => {
  it("catches render failures and displays a recovery action", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <RenderFailure fail />
      </ErrorBoundary>,
    );

    expect(screen.getByRole("alert")).toBeDefined();
    expect(screen.getByText("deliberate render failure")).toBeDefined();
    expect(screen.getByRole("button", { name: /try again/i })).toBeDefined();
  });

  it("clears the failure when navigation reset keys change", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    const view = render(
      <ErrorBoundary resetKeys={["broken-route"]}>
        <RenderFailure fail />
      </ErrorBoundary>,
    );
    expect(screen.getByRole("alert")).toBeDefined();

    view.rerender(
      <ErrorBoundary resetKeys={["safe-route"]}>
        <RenderFailure fail={false} />
      </ErrorBoundary>,
    );
    expect(screen.getByText("Recovered screen")).toBeDefined();
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
