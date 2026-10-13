#!/usr/bin/env python3
"""Use case 3: notebook-style statistical summary of the public priority API.

Shows mean tasks per priority bucket, the busiest label, and a simple attention
score that weights High/Urgent more heavily — useful for a quick health check
in a research notebook or ops script.
"""

from __future__ import annotations

import json
import statistics
import sys

import requests

PUBLIC_API_URL = "https://hestia12.pythonanywhere.com/api/charts/task-priorities/"
TIMEOUT_SECONDS = 10

# Relative weight for a rough "needs attention" score (not stored server-side).
WEIGHTS = {"Low": 1, "Medium": 2, "High": 3, "Urgent": 4}


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

    counts = [int(row["count"]) for row in rows]
    total = sum(counts)
    mean = statistics.fmean(counts) if counts else 0.0
    maximum = max(counts) if counts else 0
    busiest = [row["label"] for row in rows if int(row["count"]) == maximum]
    urgent_empty = next(
        (int(row["count"]) == 0 for row in rows if row["label"] == "Urgent"), True
    )
    attention = sum(
        int(row["count"]) * WEIGHTS.get(row["label"], 1) for row in rows
    )

    print("\nStatistical summary:")
    print(f"  Observations (priority buckets): {len(counts)}")
    print(f"  Total tasks: {total}")
    print(f"  Mean tasks per priority bucket: {mean:.2f}")
    print(f"  Max tasks in one bucket: {maximum} ({', '.join(busiest) or 'n/a'})")
    print(f"  Urgent bucket empty: {urgent_empty}")
    print(f"  Attention score (Low=1 … Urgent=4): {attention}")
    if total:
        print(
            "  Interpretation: score rises when more tasks sit in High/Urgent; "
            f"current average weight per task is {attention / total:.2f}."
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.RequestException as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
