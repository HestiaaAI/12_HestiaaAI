#!/usr/bin/env python3
"""Use case 1: pull Hestia's public priority API and aggregate workload stats.

Demonstrates that another developer can monitor household task pressure from
the production JSON without logging in or scraping HTML.
"""

from __future__ import annotations

import json
import sys

import requests

PUBLIC_API_URL = "https://hestia12.pythonanywhere.com/api/charts/task-priorities/"
TIMEOUT_SECONDS = 10


def fetch_priorities() -> list[dict]:
    print(f"GET {PUBLIC_API_URL}")
    response = requests.get(PUBLIC_API_URL, timeout=TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON list, got {type(data).__name__}")
    return data


def main() -> int:
    rows = fetch_priorities()
    print("\nRaw JSON response:")
    print(json.dumps(rows, indent=2))

    total = sum(int(row["count"]) for row in rows)
    active = [row for row in rows if int(row["count"]) > 0]
    high_urgent = sum(
        int(row["count"]) for row in rows if row["label"] in {"High", "Urgent"}
    )
    top = max(rows, key=lambda row: int(row["count"])) if rows else None

    print("\nAggregation result:")
    print(f"  Total tasks across all priorities: {total}")
    print(f"  Priorities with at least one task: {len(active)}")
    if total:
        share = 100.0 * high_urgent / total
        print(f"  High + Urgent share of workload: {high_urgent}/{total} ({share:.1f}%)")
    else:
        print("  High + Urgent share of workload: n/a (no tasks)")
    if top:
        print(f"  Largest bucket: {top['label']} ({top['count']} task(s))")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.RequestException as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
