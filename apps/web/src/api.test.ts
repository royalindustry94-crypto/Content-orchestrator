import { describe, expect, it, vi, afterEach } from "vitest";
import {
  getContentProfile,
  getExecutiveDashboard,
  getOperationsAlerts,
  getPipelineMonitor,
  getWorkerMonitor,
  listReviewGates,
  saveContentProfile,
} from "./api";

describe("review desk api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("lists awaiting review gates with bearer auth", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => [
        {
          id: "gate-1",
          workspace_id: "ws-1",
          pipeline_run_id: "run-1",
          content_item_id: "item-1",
          topic: "Topic",
          stage: "review",
          status: "awaiting",
          requested_at: "2026-07-27T00:00:00Z",
          timeout_at: null,
          decided_at: null,
          decided_by: null,
          script_hook: null,
          script_body: "Body",
          script_cta: null,
          run_status: "paused",
        },
      ],
    });
    vi.stubGlobal("fetch", fetchMock);

    const rows = await listReviewGates("token-123", "ws-1", "awaiting");
    expect(rows).toHaveLength(1);
    expect(rows[0]?.topic).toBe("Topic");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/workspaces/ws-1/review-gates?status=awaiting",
      expect.objectContaining({
        headers: expect.any(Headers),
      }),
    );
    const headers = fetchMock.mock.calls[0]?.[1]?.headers as Headers;
    expect(headers.get("Authorization")).toBe("Bearer token-123");
  });

  it("loads and saves the durable workspace content profile", async () => {
    const profile = {
      workspace_id: "ws-1",
      service_mode: "client" as const,
      business_name: "Northside Strength",
      offer: "Coaching",
      target_audience: "Busy adults",
      brand_voice: "Practical",
      target_platform: "Instagram",
      content_goal: "Generate enquiries",
      default_length_seconds: 60,
      created_by: "user-1",
      updated_by: "user-1",
      created_at: "",
      updated_at: "",
    };
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => profile,
    });
    vi.stubGlobal("fetch", fetchMock);

    await expect(getContentProfile("token-123", "ws-1")).resolves.toEqual(profile);
    await saveContentProfile("token-123", "ws-1", {
      service_mode: profile.service_mode,
      business_name: profile.business_name,
      offer: profile.offer,
      target_audience: profile.target_audience,
      brand_voice: profile.brand_voice,
      target_platform: profile.target_platform,
      content_goal: profile.content_goal,
      default_length_seconds: profile.default_length_seconds,
    });

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/workspaces/ws-1/content-profile",
      "/api/workspaces/ws-1/content-profile",
    ]);
    expect(fetchMock.mock.calls[1]?.[1]).toEqual(
      expect.objectContaining({ method: "PUT" }),
    );
  });
});

describe("operations dashboard api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("loads all four workspace-scoped operations APIs with bearer auth", async () => {
    const payloads = [
      { workers_online: 2 },
      { workers: [] },
      { active_pipelines: 1, pipelines: [] },
      { alerts: [] },
    ];
    const fetchMock = vi
      .fn()
      .mockImplementation(async () => ({
        ok: true,
        status: 200,
        json: async () => payloads.shift(),
      }));
    vi.stubGlobal("fetch", fetchMock);

    await getExecutiveDashboard("ops-token", "ws-7");
    await getWorkerMonitor("ops-token", "ws-7");
    await getPipelineMonitor("ops-token", "ws-7");
    await getOperationsAlerts("ops-token", "ws-7");

    expect(fetchMock.mock.calls.map((call) => call[0])).toEqual([
      "/api/workspaces/ws-7/operations/executive",
      "/api/workspaces/ws-7/operations/workers",
      "/api/workspaces/ws-7/operations/pipelines",
      "/api/workspaces/ws-7/operations/alerts",
    ]);
    for (const call of fetchMock.mock.calls) {
      const headers = call[1]?.headers as Headers;
      expect(headers.get("Authorization")).toBe("Bearer ops-token");
    }
  });

  it("surfaces backend failures instead of rendering fake data", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        statusText: "Service Unavailable",
        text: async () => "database unavailable",
      }),
    );

    await expect(getExecutiveDashboard("token", "ws")).rejects.toThrow(
      "503: database unavailable",
    );
  });
});
