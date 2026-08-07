import type {
  ActivityFeed,
  ContentCommand,
  CostControl,
  Customers,
  ExecutiveDashboard,
  ExecutiveInsights,
  ExecutiveMode,
  GitHubOut,
  Leads,
  LiveLogs,
  PipelineMonitor,
  SpendDashboard,
  SystemHealth,
  WorkerMonitor,
  WorkerTimeline,
} from "./api";

/**
 * Pure view-model helpers for the dashboard shell.
 *
 * These are deliberately framework-free so navigation safety (stale-data
 * guards) and the truthful health indicator can be unit-tested without a DOM.
 */

export type DashboardData = {
  executive: ExecutiveDashboard;
  pipelines: PipelineMonitor;
  alerts: import("./api").Alerts;
  activity: ActivityFeed;
  health: SystemHealth;
  customers: Customers;
};

export type HealthLevel = "operational" | "degraded" | "down" | "unknown";

export function healthStatusToLevel(status: string): "good" | "warn" | "bad" {
  const normalized = status.toLowerCase();
  if (["red", "critical", "offline", "failed", "down", "error"].includes(normalized)) return "bad";
  if (["amber", "warn", "warning", "yellow", "degraded"].includes(normalized)) return "warn";
  return "good";
}

/**
 * Collapse every backend health indicator into a single, truthful status.
 * Worst-status-wins: any failing indicator means the workspace is *not*
 * "operational", eliminating the previous hardcoded "All systems operational".
 */
export function aggregateHealth(health: SystemHealth | null): HealthLevel {
  if (!health || health.indicators.length === 0) return "unknown";
  const levels = health.indicators.map((indicator) => healthStatusToLevel(indicator.status));
  if (levels.includes("bad")) return "down";
  if (levels.includes("warn")) return "degraded";
  return "operational";
}

export const HEALTH_COPY: Record<HealthLevel, { label: string; orb: string }> = {
  operational: { label: "All systems operational", orb: "good" },
  degraded: { label: "Degraded performance", orb: "warn" },
  down: { label: "Service disruption detected", orb: "bad" },
  unknown: { label: "Checking system status…", orb: "unknown" },
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

export function isDashboardData(value: unknown): value is DashboardData {
  return isRecord(value) && "executive" in value && "alerts" in value && "activity" in value && "health" in value;
}

export function isExecutiveMode(value: unknown): value is ExecutiveMode {
  return isRecord(value) && Array.isArray((value as ExecutiveMode).health) && "critical_alerts" in value;
}

export function isActivityFeed(value: unknown): value is ActivityFeed {
  return isRecord(value) && Array.isArray((value as ActivityFeed).items);
}

export function isLiveLogs(value: unknown): value is LiveLogs {
  return isRecord(value) && Array.isArray((value as LiveLogs).logs);
}

export function isContentCommand(value: unknown): value is ContentCommand {
  return isRecord(value) && "ideas" in value && "published" in value;
}

export function isPipelineMonitor(value: unknown): value is PipelineMonitor {
  return isRecord(value) && Array.isArray((value as PipelineMonitor).pipelines);
}

export function isWorkersData(value: unknown): value is { monitor: WorkerMonitor; timeline: WorkerTimeline } {
  return isRecord(value) && "monitor" in value && "timeline" in value;
}

export function isCustomers(value: unknown): value is Customers {
  return isRecord(value) && Array.isArray((value as Customers).customers);
}

export function isLeads(value: unknown): value is Leads {
  return isRecord(value) && Array.isArray((value as Leads).leads);
}

export function isAnalyticsData(
  value: unknown,
): value is { insights: ExecutiveInsights; activity: ActivityFeed; github: GitHubOut } {
  return isRecord(value) && "insights" in value && "github" in value;
}

export function isBillingData(value: unknown): value is { spend: SpendDashboard; cost: CostControl } {
  return isRecord(value) && "spend" in value && "cost" in value;
}

export function isSettingsData(value: unknown): value is { health: SystemHealth; executive: ExecutiveDashboard } {
  return isRecord(value) && "health" in value && "executive" in value && !("alerts" in value);
}
