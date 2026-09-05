// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";

const originalFetch = window.fetch;

describe("creative preview adapter", () => {
  afterEach(() => {
    window.fetch = originalFetch;
    vi.resetModules();
    vi.unstubAllEnvs();
    vi.unstubAllGlobals();
  });

  it("stays inert when the preview build flag is unset", async () => {
    vi.stubEnv("VITE_CREATIVE_PREVIEW", "");
    const { isCreativePreview, installCreativePreviewFetch } = await import("./creativePreview");
    const original = window.fetch;
    installCreativePreviewFetch();
    expect(isCreativePreview()).toBe(false);
    expect(window.fetch).toBe(original);
  });

  it("signs in and keeps Home financial circles disconnected", async () => {
    vi.stubEnv("VITE_CREATIVE_PREVIEW", "1");
    const { isCreativePreview, installCreativePreviewFetch } = await import("./creativePreview");
    expect(isCreativePreview()).toBe(true);
    installCreativePreviewFetch();

    const login = await fetch("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email: "founder@preview.local", password: "preview-only" }),
    });
    const token = await login.json() as { access_token: string; email: string };
    expect(token.access_token).toBe("preview-visual-token");
    expect(token.email).toBe("founder@preview.local");

    const workspaces = await (await fetch("/api/workspaces")).json() as Array<{ id: string }>;
    expect(workspaces[0]?.id).toBe("preview-ws");

    const action = await (await fetch("/api/workspaces/preview-ws/operations/actions/emergency-stop", {
      method: "POST",
    })).json() as { ok: boolean; affected: number };
    expect(action.ok).toBe(false);
    expect(action.affected).toBe(0);
  });

  it("keeps Human Review decisions in memory and refuses publish side effects", async () => {
    vi.stubEnv("VITE_CREATIVE_PREVIEW", "1");
    const { installCreativePreviewFetch } = await import("./creativePreview");
    installCreativePreviewFetch();

    const awaiting = await (await fetch("/api/workspaces/preview-ws/review-gates?status=awaiting")).json() as Array<{ id: string; status: string; topic: string }>;
    expect(awaiting[0]?.status).toBe("awaiting");
    expect(awaiting[0]?.topic).toMatch(/PREVIEW DATA/);

    const decided = await (await fetch(`/api/workspaces/preview-ws/review-gates/${awaiting[0].id}/decision`, {
      method: "POST",
      body: JSON.stringify({ approved: true }),
    })).json() as { status: string };
    expect(decided.status).toBe("approved");

    const remaining = await (await fetch("/api/workspaces/preview-ws/review-gates?status=awaiting")).json() as unknown[];
    expect(remaining).toEqual([]);
  });
});
