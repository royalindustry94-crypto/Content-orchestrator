import { describe, expect, it, vi, afterEach } from "vitest";
import { listReviewGates } from "./api";

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
