#!/usr/bin/env python3
"""Use case 2: export the public priority API to a CSV for Excel / Google Sheets.

Someone else can import the CSV (File > Import / Open) and build their own
pivot tables or charts without using Vega-Lite or Hestia's UI.
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import requests

PUBLIC_API_URL = "https://hestia12.pythonanywhere.com/api/charts/task-priorities/"
TIMEOUT_SECONDS = 10
OUTPUT_CSV = Path(__file__).resolve().parent.parent / "outputs" / "task_priorities.csv"


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

    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["label", "count"])
        writer.writeheader()
        for row in rows:
            writer.writerow({"label": row["label"], "count": int(row["count"])})

    print(f"\nCSV written for spreadsheet import:")
    print(f"  {OUTPUT_CSV}")
    print("\nCSV contents:")
    print(OUTPUT_CSV.read_text(encoding="utf-8"))
    print("Next step: open this file in Excel or File > Import in Google Sheets.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except requests.RequestException as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
