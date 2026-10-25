"""90-row Hugging Face API costs on Person 2's inference-tier workload.

Shared fields come from a7/person2/cost_assumptions.json:
one request per user, 256 input tokens, 500 output tokens, and
assumptions id hestia-a7-256in-500out-r1-inference-only-v1.

Token price is the Hugging Face Inference Providers listing for
meta-llama/Llama-3.1-8B-Instruct on Novita, observed 2026-10-23:
$0.02 per million input tokens and $0.05 per million output tokens.
The fifteen local model ids are not all on that catalog, so every row
uses this one comparable hosted model.

The gateway is a separate 2-vCPU Runpod CPU pod. It is the API-side
stand-in for the thin handler that local hosting co-locates on the GPU
pod. Django, the frontend, and the database stay out of both totals.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

from a7.benchmark_contract import MODEL_REGISTRY

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "a7" / "results" / "api_costs.csv"
LOCAL = ROOT / "a7" / "results" / "local_costs.csv"
SUMMARY = Path(__file__).resolve().parent / "results" / "api_vs_local.json"
ASSUMPTIONS = ROOT / "a7" / "person2" / "cost_assumptions.json"

COMPARABLE = "meta-llama/Llama-3.1-8B-Instruct"
INPUT_USD_PER_MILLION = 0.02
OUTPUT_USD_PER_MILLION = 0.05
# Documented Runpod catalog example: Gen 3 Compute-Optimized, $0.04 per
# secure-cloud vCPU-hour. The smallest listed size is 2 vCPU.
GATEWAY_VCPU = 2
GATEWAY_USD_PER_VCPU_HOUR = 0.04
GATEWAY_DISK_GB = 20
GATEWAY_DISK_USD_PER_GB_MONTH = 0.10
# Planning capacity for the HTTP forwarder only. Not a measured benchmark.
GATEWAY_REQUESTS_PER_SECOND = 50


def gateway_machines(daily_requests: int, config: dict) -> int:
    effective = (
        GATEWAY_REQUESTS_PER_SECOND
        * config["target_utilization"]
        / config["service_time_penalty"]
    )
    counted = math.ceil(
        daily_requests * config["peak_to_average"] / (86400 * effective)
    )
    return max(config["minimum_replicas"], counted) + config["standby_replicas"]


def main() -> None:
    config = json.loads(ASSUMPTIONS.read_text())
    requests_per_user = config["requests_per_user"]
    input_tokens = config["input_tokens_per_request"]
    output_tokens = config["output_tokens_per_request"]
    assumptions_id = config["assumptions_id"]
    hours = config["hours_per_day"]
    days = config["days_per_month"]
    gateway_compute_day = GATEWAY_VCPU * GATEWAY_USD_PER_VCPU_HOUR * hours
    gateway_disk_day = GATEWAY_DISK_GB * GATEWAY_DISK_USD_PER_GB_MONTH / days
    gateway_day = gateway_compute_day + gateway_disk_day
    source = (
        f"{assumptions_id}; workload from a7/person2/cost_assumptions.json "
        f"({requests_per_user} request/user, {input_tokens} input, {output_tokens} output). "
        "HF Inference Providers catalog 2026-10-23: "
        f"{COMPARABLE} via Novita, input ${INPUT_USD_PER_MILLION}/1M and "
        f"output ${OUTPUT_USD_PER_MILLION}/1M. The local roster ids are not all listed, "
        "so this one comparable rate is used for every model. "
        "Gateway: Runpod CPU catalog example cpu3c, "
        f"${GATEWAY_USD_PER_VCPU_HOUR}/vCPU-hour secure cloud, {GATEWAY_VCPU} vCPU, "
        f"{GATEWAY_DISK_GB} GB container disk at ${GATEWAY_DISK_USD_PER_GB_MONTH}/GB-month "
        "(https://docs.runpod.io/api-reference-v2/catalog/list-cpu-types and "
        "https://docs.runpod.io/pods/pricing). "
        f"Gateway throughput {GATEWAY_REQUESTS_PER_SECOND} requests/second is an assumption, "
        "sized with Person 2's utilization, peak, and service-time factors. "
        "Excludes the shared Django/frontend/database baseline, egress, tax, labor, "
        "monitoring, and redundancy."
    )
    traffic = {
        "Prototype": 1_000,
        "Early Startup": 10_000,
        "Growing Product": 100_000,
        "Large Platform": 1_000_000,
        "Mass Consumer App": 10_000_000,
        "Global Platform": 100_000_000,
    }
    rows = []
    for model in MODEL_REGISTRY:
        for category, users in traffic.items():
            requests = users * requests_per_user
            inference = (
                requests * input_tokens / 1_000_000 * INPUT_USD_PER_MILLION
                + requests * output_tokens / 1_000_000 * OUTPUT_USD_PER_MILLION
            )
            machines = gateway_machines(requests, config)
            machine_cost = machines * gateway_day
            rows.append({
                "model_id": model["model_id"],
                "model_category": model["category"],
                "parameter_billions": model["params_b"],
                "local_llm_model_size": model["category"],
                "comparable_paid_model": COMPARABLE,
                "hosted_on_hugging_face": "yes",
                "cost_per_million_input_tokens_usd": INPUT_USD_PER_MILLION,
                "cost_per_million_output_tokens_usd": OUTPUT_USD_PER_MILLION,
                "traffic_category": category,
                "daily_active_users": users,
                "requests_per_user": requests_per_user,
                "input_tokens_per_request": input_tokens,
                "output_tokens_per_request": output_tokens,
                "avg_tokens_per_user": requests_per_user * output_tokens,
                "total_daily_requests": requests,
                "total_daily_input_tokens": requests * input_tokens,
                "total_daily_output_tokens": requests * output_tokens,
                "total_daily_token_load": requests * output_tokens,
                "estimated_api_inference_cost_usd": round(inference, 6),
                "gateway_machine": "Runpod cpu3c 2 vCPU",
                "gateway_requests_per_second_assumed": GATEWAY_REQUESTS_PER_SECOND,
                "machines_required_api_infrastructure": machines,
                "api_gateway_compute_usd_day": round(machines * gateway_compute_day, 6),
                "api_gateway_storage_usd_day": round(machines * gateway_disk_day, 6),
                "api_machine_cost_usd": round(machine_cost, 6),
                "total_daily_cost_usd": round(inference + machine_cost, 6),
                "assumptions_id": assumptions_id,
                "scope": "inference tier only; token API plus CPU gateway",
                "source_or_assumption": source,
            })
    if len(rows) != 90:
        raise SystemExit(f"expected 90 rows, got {len(rows)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = _compare_local(rows)
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"Wrote {len(rows)} rows to {OUT}")
    print(json.dumps(summary["by_traffic"], indent=2))


def _compare_local(api_rows: list[dict]) -> dict:
    """Same join keys as architecture_analysis.compare_costs."""
    local_rows = list(csv.DictReader(LOCAL.open(newline="", encoding="utf-8")))
    keys = (
        "model_id", "traffic_category", "daily_active_users", "requests_per_user",
        "input_tokens_per_request", "output_tokens_per_request", "assumptions_id",
    )
    local = {tuple(row[key] for key in keys): row for row in local_rows}
    paired = []
    for row in api_rows:
        key = tuple(str(row[key]) for key in keys)
        match = local.get(key)
        if match is None:
            raise SystemExit(f"no local row for {key}")
        local_cost = float(match["total_daily_cost_usd"])
        api_cost = float(row["total_daily_cost_usd"])
        cheaper = "local" if local_cost < api_cost else "api" if api_cost < local_cost else "tie"
        paired.append({
            "model_id": row["model_id"],
            "traffic_category": row["traffic_category"],
            "daily_active_users": row["daily_active_users"],
            "local_usd": local_cost,
            "api_usd": api_cost,
            "cheaper": cheaper,
        })
    if len(paired) != 90:
        raise SystemExit(f"expected 90 joined rows, got {len(paired)}")
    by_traffic = {}
    for item in paired:
        bucket = by_traffic.setdefault(item["traffic_category"], {"api": 0, "local": 0, "tie": 0})
        bucket[item["cheaper"]] += 1
    return {"joined_rows": len(paired), "by_traffic": by_traffic, "rows": paired}


if __name__ == "__main__":
    main()
