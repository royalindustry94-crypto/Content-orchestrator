// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";

import LumoraDashboard from "./LumoraDashboard";
import { FOUNDER_STUDIO_PREVIEW_TOKEN, FOUNDER_STUDIO_PREVIEW_WORKSPACE } from "./preview/session";
import { clearPreviewStore, resetPreviewStore } from "./preview/store";

const api = vi.hoisted(() => ({
  getExecutiveDashboard: vi.fn(),
  getPipelineMonitor: vi.fn(),
  getOperationsAlerts: vi.fn(),
  getActivityFeed: vi.fn(),
  getSystemHealth: vi.fn(),
  getCustomers: vi.fn(),
  listWorkspaces: vi.fn(),
  getNotifications: vi.fn(),
  listReviewGates: vi.fn(),
}));

vi.mock("./api", () => api);

function renderPreview() {
  return render(
    <LumoraDashboard
      token={FOUNDER_STUDIO_PREVIEW_TOKEN}
      workspaceId={FOUNDER_STUDIO_PREVIEW_WORKSPACE}
      email="Founder Preview"
      onWorkspaceChange={() => {}}
      onSignOut={() => {}}
    />,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  clearPreviewStore();
  resetPreviewStore();
});

afterEach(() => {
  cleanup();
});

describe("Founder Studio preview data layer", () => {
  it("loads Home from the isolated store and never calls FastAPI", async () => {
    renderPreview();
    expect(await screen.findByRole("heading", { name: "Home" })).toBeDefined();
    expect(screen.getAllByText(/AI PROVIDER NOT CONFIGURED/i).length).toBeGreaterThan(0);
    expect(screen.getByText(/Browser-local demo data/i)).toBeDefined();
    expect(api.getExecutiveDashboard).not.toHaveBeenCalled();
    expect(api.getCustomers).not.toHaveBeenCalled();
    expect(api.listReviewGates).not.toHaveBeenCalled();
    expect(screen.queryByText(/We couldn't load this view/i)).toBeNull();
  });

  it("creates a customer, content, review approval, and ready queue without publishing", async () => {
    renderPreview();
    await screen.findByRole("heading", { name: "Home" });

    fireEvent.click(within(screen.getByRole("navigation", { name: /primary navigation/i })).getByRole("button", { name: /^Customers$/i }));
    expect(await screen.findByRole("heading", { name: /Create a fake customer/i })).toBeDefined();

    fireEvent.change(screen.getByLabelText(/Customer \/ business name/i), { target: { value: "Harbor Studio" } });
    fireEvent.change(screen.getByLabelText(/^Niche$/i), { target: { value: "Brand films" } });
    fireEvent.click(screen.getByRole("button", { name: /Save fake customer/i }));
    expect(await screen.findByText("Harbor Studio")).toBeDefined();

    fireEvent.click(within(screen.getByRole("navigation", { name: /primary navigation/i })).getByRole("button", { name: /^Create$/i }));
    expect(await screen.findByText(/AI PROVIDER NOT CONFIGURED/i)).toBeDefined();
    fireEvent.change(screen.getByLabelText(/Idea \/ topic/i), { target: { value: "Monday reel" } });
    fireEvent.change(screen.getByLabelText(/^Hook$/i), { target: { value: "Stop posting without a hook" } });
    fireEvent.change(screen.getByLabelText(/Caption \/ script \/ body/i), { target: { value: "Manual draft written by the Founder." } });
    fireEvent.change(screen.getByLabelText(/^CTA$/i), { target: { value: "Comment BRIEF" } });
    fireEvent.click(screen.getByRole("button", { name: /Save draft/i }));
    expect(await screen.findByText(/Saved as Draft/i)).toBeDefined();
    const monday = screen.getByText("Monday reel").closest("li");
    if (!monday) throw new Error("Monday reel row missing");
    fireEvent.click(within(monday).getByRole("button", { name: /Submit for review/i }));
    expect(await screen.findByText(/Submitted for review/i)).toBeDefined();

    fireEvent.click(within(screen.getByRole("navigation", { name: /primary navigation/i })).getByRole("button", { name: /^Review$/i }));
    expect(await screen.findByText(/Approval is a deliberate Founder action/i)).toBeDefined();
    fireEvent.click(screen.getAllByRole("button", { name: "APPROVE" })[0]);
    expect(await screen.findByText(/Moved to Ready to Publish/i)).toBeDefined();
    expect(screen.getByText(/No platform was called/i)).toBeDefined();

    fireEvent.click(within(screen.getByRole("navigation", { name: /primary navigation/i })).getByRole("button", { name: /Ready to Publish/i }));
    expect(await screen.findByText(/Approved by the Founder/i)).toBeDefined();
    expect(screen.getByText("Monday reel")).toBeDefined();
    expect(screen.getByText(/no social platform API called/i)).toBeDefined();
    expect(api.getExecutiveDashboard).not.toHaveBeenCalled();
  });

  it("keeps preview records after a remount so refresh does not break the UI", async () => {
    const first = renderPreview();
    await screen.findByRole("heading", { name: "Home" });
    fireEvent.click(within(screen.getByRole("navigation", { name: /primary navigation/i })).getByRole("button", { name: /^Customers$/i }));
    fireEvent.change(screen.getByLabelText(/Customer \/ business name/i), { target: { value: "Kept After Refresh" } });
    fireEvent.click(screen.getByRole("button", { name: /Save fake customer/i }));
    await screen.findByText("Kept After Refresh");
    first.unmount();

    renderPreview();
    fireEvent.click(within(screen.getByRole("navigation", { name: /primary navigation/i })).getByRole("button", { name: /^Customers$/i }));
    expect(await screen.findByText("Kept After Refresh")).toBeDefined();
    expect(screen.queryByText(/We couldn't load this view/i)).toBeNull();
  });
});
