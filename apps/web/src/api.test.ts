import { describe, expect, it, vi, afterEach } from "vitest";
import {
  getExecutiveDashboard,
  getOperationsAlerts,
  getPipelineMonitor,
  getWorkerMonitor,
  listReviewGates,
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
