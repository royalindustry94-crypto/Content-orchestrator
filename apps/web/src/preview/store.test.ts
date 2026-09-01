import { beforeEach, describe, expect, it } from "vitest";

import {
  approvePreviewContent,
  clearPreviewStore,
  contentReadyToPublish,
  loadPreviewStore,
  resetPreviewStore,
  submitPreviewForReview,
  upsertContent,
  upsertCustomer,
} from "./store";

describe("founder studio preview store", () => {
  beforeEach(() => {
    clearPreviewStore();
    resetPreviewStore();
  });

  it("seeds a labelled demo customer and does not claim a live AI provider", () => {
    const store = loadPreviewStore();
    expect(store.customers[0]?.name).toContain("DEMO");
    expect(store.content[0]?.origin).toBe("demo_generated");
    expect(store.content[0]?.body).toContain("no AI provider ran");
  });

  it("creates a customer and content, then requires deliberate approval", () => {
    const customer = upsertCustomer({
      name: "Harbor Studio",
      niche: "Brand films",
      audience: "Founders",
      tone: "Direct",
      goals: "Weekly reels",
      platforms: ["instagram", "youtube"],
    });
    const item = upsertContent({
      customerId: customer.id,
      topic: "Monday reel",
      platform: "instagram",
      hook: "Stop posting without a hook",
      body: "Manual draft written by the Founder.",
      cta: "Comment BRIEF",
      status: "draft",
      origin: "manual",
    });
    expect(item.status).toBe("draft");
    expect(() => approvePreviewContent(item.id)).toThrow(/Review/);
    const submitted = submitPreviewForReview(item.id);
    expect(submitted.status).toBe("review");
    const approved = approvePreviewContent(item.id);
    expect(approved.status).toBe("ready_to_publish");
    expect(contentReadyToPublish(loadPreviewStore()).map((row) => row.id)).toEqual([item.id]);
  });

  it("never publishes and locks ready items", () => {
    const store = loadPreviewStore();
    const draft = store.content[0];
    if (!draft) throw new Error("seed missing");
    submitPreviewForReview(draft.id);
    approvePreviewContent(draft.id);
    expect(() =>
      upsertContent({
        id: draft.id,
        customerId: draft.customerId,
        topic: "changed",
        platform: draft.platform,
        hook: draft.hook,
        body: draft.body,
        cta: draft.cta,
        status: "draft",
        origin: "manual",
      }),
    ).toThrow(/locked/);
  });
});
