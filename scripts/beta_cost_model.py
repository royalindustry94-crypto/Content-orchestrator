#!/usr/bin/env python3
"""Compute Lumora beta unit economics from measured CSV inputs only.

No default provider pricing, usage, revenue, support, or margin assumptions are
embedded here. Missing measurements are emitted as N/M rather than estimated.

Inputs:
  --cost-events       Normalized actual-cost event CSV (one immutable event/row)
  --accepted-outputs  Human-Review-Gate outcome CSV (one output/item/row)
  --pricing           Optional explicit workspace-month revenue/threshold CSV
  --output            Destination CSV with workspace-month economics

See docs/BETA_COST_MEASUREMENT_SPEC.md for the input contracts and extraction
rules. This script deliberately refuses duplicate event IDs and invalid costs so
retries and reconciliation mistakes cannot silently inflate costs.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

COST_BUCKETS = (
    "llm",
    "tts",
    "image_video",
    "render",
    "storage",
    "retry_failure",
    "support",
    "other",
)

COST_REQUIRED = {
    "event_id",
    "occurred_at_utc",
    "workspace_id",
    "content_item_id",
    "cost_bucket",
    "cost_usd",
    "outcome",
    "source_record_type",
    "source_record_id",
    "reconciliation_status",
}
OUTPUT_REQUIRED = {"workspace_id", "content_item_id", "hrg_status", "decided_at_utc"}
PRICING_REQUIRED = {
    "workspace_id",
    "month_utc",
    "monthly_revenue_usd",
    "included_accepted_outputs",
    "overage_per_accepted_output_usd",
    "throttle_cost_threshold_usd",
    "hard_spend_cap_usd",
}


@dataclass
class Totals:
    bucket_costs: dict[str, Decimal] = field(
        default_factory=lambda: defaultdict(lambda: Decimal("0"))
    )
    total_cost: Decimal = Decimal("0")
    cost_event_count: int = 0
    failed_or_retry_event_count: int = 0
    accepted_items: set[str] = field(default_factory=set)


def _read_rows(path: Path, required: set[str]) -> list[dict[str, str]]:
    if not path.exists():
        raise ValueError(f"input file does not exist: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        headers = set(reader.fieldnames or [])
        missing = sorted(required - headers)
        if missing:
            raise ValueError(f"{path}: missing required columns: {', '.join(missing)}")
        return list(reader)


def _month(value: str) -> str:
    if len(value) < 7 or value[4] != "-":
        raise ValueError(f"timestamp/month must begin YYYY-MM: {value!r}")
    return value[:7]


def _money(value: str, *, field_name: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except (InvalidOperation, TypeError) as exc:
        raise ValueError(f"{field_name} must be a decimal, got {value!r}") from exc
    if parsed < 0:
        raise ValueError(f"{field_name} must not be negative, got {value!r}")
    return parsed


def _decimal_text(value: Decimal | None) -> str:
    if value is None:
        return "N/M"
    return f"{value.quantize(Decimal('0.0001'))}"


def _load_pricing(path: Path | None) -> dict[tuple[str, str], dict[str, Decimal]]:
    if path is None:
        return {}
    rows = _read_rows(path, PRICING_REQUIRED)
    pricing: dict[tuple[str, str], dict[str, Decimal]] = {}
    for row in rows:
        key = (row["workspace_id"].strip(), _month(row["month_utc"].strip()))
        if not all(key):
            raise ValueError(f"{path}: workspace_id and month_utc are required")
        if key in pricing:
            raise ValueError(f"{path}: duplicate pricing row for {key[0]} {key[1]}")
        pricing[key] = {
            "revenue": _money(row["monthly_revenue_usd"], field_name="monthly_revenue_usd"),
            "included": _money(
                row["included_accepted_outputs"], field_name="included_accepted_outputs"
            ),
            "overage": _money(
                row["overage_per_accepted_output_usd"], field_name="overage_per_accepted_output_usd"
            ),
            "throttle": _money(
                row["throttle_cost_threshold_usd"], field_name="throttle_cost_threshold_usd"
            ),
            "hard_cap": _money(row["hard_spend_cap_usd"], field_name="hard_spend_cap_usd"),
        }
    return pricing


def build_report(
    cost_events: list[dict[str, str]],
    accepted_outputs: list[dict[str, str]],
    pricing: dict[tuple[str, str], dict[str, Decimal]],
) -> list[dict[str, str]]:
    totals: dict[tuple[str, str], Totals] = defaultdict(Totals)
    seen_event_ids: set[str] = set()

    for row in cost_events:
        event_id = row["event_id"].strip()
        key = (row["workspace_id"].strip(), _month(row["occurred_at_utc"].strip()))
        bucket = row["cost_bucket"].strip()
        if not event_id or not all(key):
            raise ValueError("cost event requires non-empty event_id, workspace_id, and occurred_at_utc")
        if event_id in seen_event_ids:
            raise ValueError(f"duplicate cost event_id: {event_id}")
        if bucket not in COST_BUCKETS:
            raise ValueError(f"unsupported cost_bucket {bucket!r}; expected one of {', '.join(COST_BUCKETS)}")
        seen_event_ids.add(event_id)
        amount = _money(row["cost_usd"], field_name=f"cost_usd for {event_id}")
        tally = totals[key]
        tally.bucket_costs[bucket] += amount
        tally.total_cost += amount
        tally.cost_event_count += 1
        if row["outcome"].strip().lower() in {"failed", "retry", "timed_out", "dead_letter"}:
            tally.failed_or_retry_event_count += 1

    accepted_seen: set[tuple[str, str, str]] = set()
    for row in accepted_outputs:
        status = row["hrg_status"].strip().lower()
        if status != "approved":
            continue
        key = (row["workspace_id"].strip(), _month(row["decided_at_utc"].strip()))
        item_id = row["content_item_id"].strip()
        output_key = (key[0], key[1], item_id)
        if not all(key) or not item_id:
            raise ValueError("accepted output requires workspace_id, content_item_id, and decided_at_utc")
        if output_key in accepted_seen:
            raise ValueError(f"duplicate approved output record: {output_key}")
        accepted_seen.add(output_key)
        totals[key].accepted_items.add(item_id)

    all_keys = sorted(set(totals) | set(pricing))
    report: list[dict[str, str]] = []
    for key in all_keys:
        tally = totals[key]
        price = pricing.get(key)
        accepted_count = len(tally.accepted_items)
        cost_per_accepted = tally.total_cost / accepted_count if accepted_count else None
        revenue = price["revenue"] if price is not None else None
        gross_margin = (
            (revenue - tally.total_cost) / revenue
            if revenue is not None and revenue > 0
            else None
        )
        overage_outputs = (
            max(Decimal(accepted_count) - price["included"], Decimal("0"))
            if price is not None
            else None
        )
        throttle = "N/M"
        if price is not None:
            throttle = "yes" if tally.total_cost >= price["throttle"] else "no"
        report.append(
            {
                "workspace_id": key[0],
                "month_utc": key[1],
                "accepted_outputs": str(accepted_count),
                "cost_per_accepted_output_usd": _decimal_text(cost_per_accepted),
                "cost_per_workspace_usd": _decimal_text(tally.total_cost),
                "monthly_revenue_usd": _decimal_text(revenue),
                "monthly_gross_margin": _decimal_text(gross_margin),
                "included_accepted_outputs": _decimal_text(price["included"] if price else None),
                "overage_outputs": _decimal_text(overage_outputs),
                "overage_per_accepted_output_usd": _decimal_text(price["overage"] if price else None),
                "throttle_required": throttle,
                "hard_spend_cap_usd": _decimal_text(price["hard_cap"] if price else None),
                "cost_events": str(tally.cost_event_count),
                "failed_or_retry_events": str(tally.failed_or_retry_event_count),
                **{f"{bucket}_cost_usd": _decimal_text(tally.bucket_costs[bucket]) for bucket in COST_BUCKETS},
            }
        )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cost-events", required=True, type=Path)
    parser.add_argument("--accepted-outputs", required=True, type=Path)
    parser.add_argument("--pricing", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    try:
        report = build_report(
            _read_rows(args.cost_events, COST_REQUIRED),
            _read_rows(args.accepted_outputs, OUTPUT_REQUIRED),
            _load_pricing(args.pricing),
        )
    except ValueError as exc:
        print(f"input error: {exc}", file=sys.stderr)
        return 2

    fields = [
        "workspace_id",
        "month_utc",
        "accepted_outputs",
        "cost_per_accepted_output_usd",
        "cost_per_workspace_usd",
        "monthly_revenue_usd",
        "monthly_gross_margin",
        "included_accepted_outputs",
        "overage_outputs",
        "overage_per_accepted_output_usd",
        "throttle_required",
        "hard_spend_cap_usd",
        "cost_events",
        "failed_or_retry_events",
        *[f"{bucket}_cost_usd" for bucket in COST_BUCKETS],
    ]
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report)
    print(f"wrote {len(report)} workspace-month rows to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
