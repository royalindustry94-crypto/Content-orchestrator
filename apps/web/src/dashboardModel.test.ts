import { describe, expect, it } from "vitest";
import {
  HEALTH_COPY,
  aggregateHealth,
  healthStatusToLevel,
  isActivityFeed,
  isBillingData,
  isContentCommand,
  isCustomers,
  isDashboardData,
  isExecutiveMode,
  isLeads,
  isLiveLogs,
  isPipelineMonitor,
  isSettingsData,
  isWorkersData,
} from "./dashboardModel";
import type { SystemHealth } from "./api";

function health(...statuses: string[]): SystemHealth {
  return {
    indicators: statuses.map((status, index) => ({
      key: `k${index}`,
      label: `Indicator ${index}`,
      status,
      detail: "",
    })),
    generated_at: "2026-08-07T00:00:00Z",
  };
}

describe("aggregateHealth — truthful system status", () => {
  it("reports operational only when every indicator is healthy", () => {
    expect(aggregateHealth(health("green", "green", "green"))).toBe("operational");
    expect(HEALTH_COPY.operational.label).toBe("All systems operational");
  });

  it("never claims operational when a worker/subsystem is red", () => {
    const level = aggregateHealth(health("green", "green", "red", "green"));
    expect(level).toBe("down");
    expect(HEALTH_COPY[level].label).not.toBe("All systems operational");
  });

  it("degrades (not down) when only warnings are present", () => {
    expect(aggregateHealth(health("green", "amber", "green"))).toBe("degraded");
    expect(aggregateHealth(health("green", "warning"))).toBe("degraded");
  });

  it("returns unknown when health has not loaded yet", () => {
    expect(aggregateHealth(null)).toBe("unknown");
    expect(aggregateHealth(health())).toBe("unknown");
  });

  it("maps individual statuses to severity buckets", () => {
    expect(healthStatusToLevel("critical")).toBe("bad");
    expect(healthStatusToLevel("offline")).toBe("bad");
    expect(healthStatusToLevel("degraded")).toBe("warn");
    expect(healthStatusToLevel("green")).toBe("good");
  });
});

// Representative payloads for each route.
const dashboardPayload = {
  executive: { jobs_running: 0 },
  pipelines: { pipelines: [], jobs_completed: 0 },
  alerts: { alerts: [] },
  activity: { items: [] },
  health: { indicators: [] },
  customers: { revenue_mtd_usd: "0" },
};
const executiveModePayload = { health: [], critical_alerts: 0 };
const pipelinePayload = { pipelines: [], active_pipelines: 0 };
const workersPayload = { monitor: { workers: [] }, timeline: { workers: [] } };
const customersPayload = { customers: [] };
const leadsPayload = { leads: [], total: 0 };
const billingPayload = { spend: {}, cost: {} };
const settingsPayload = { health: { indicators: [] }, executive: { deployment: {} } };

describe("route type guards — prevent stale-data crashes on navigation", () => {
  it("accepts the payload for its own route", () => {
    expect(isDashboardData(dashboardPayload)).toBe(true);
    expect(isExecutiveMode(executiveModePayload)).toBe(true);
    expect(isPipelineMonitor(pipelinePayload)).toBe(true);
    expect(isWorkersData(workersPayload)).toBe(true);
    expect(isCustomers(customersPayload)).toBe(true);
    expect(isLeads(leadsPayload)).toBe(true);
    expect(isBillingData(billingPayload)).toBe(true);
    expect(isSettingsData(settingsPayload)).toBe(true);
  });

  it("rejects a previous route's payload so the view falls back to loading instead of crashing", () => {
    // The exact crash from the audit: dashboard data cast into PipelinesView.
    expect(isPipelineMonitor(dashboardPayload)).toBe(false);
    // Dashboard data cast into Mission Control overview (ExecutiveMode).
    expect(isExecutiveMode(dashboardPayload)).toBe(false);
    // Workers/customers/leads shapes are not interchangeable.
    expect(isWorkersData(customersPayload)).toBe(false);
    expect(isCustomers(pipelinePayload)).toBe(false);
    expect(isLeads(workersPayload)).toBe(false);
    // Dashboard vs settings share health+executive but dashboard has alerts.
    expect(isSettingsData(dashboardPayload)).toBe(false);
  });

  it("rejects null/undefined without throwing", () => {
    for (const guard of [
      isDashboardData,
      isExecutiveMode,
      isActivityFeed,
      isLiveLogs,
      isContentCommand,
      isPipelineMonitor,
      isWorkersData,
      isCustomers,
      isLeads,
      isBillingData,
      isSettingsData,
    ]) {
      expect(guard(null)).toBe(false);
      expect(guard(undefined)).toBe(false);
    }
  });
});
