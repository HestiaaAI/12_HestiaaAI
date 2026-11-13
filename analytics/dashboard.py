"""Reproducible request metrics for the AI analytics assignment."""
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
from math import ceil
from random import Random
from statistics import mean, quantiles

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_safe

FEATURES = ("Ask Hestia", "Meal Ideas", "Brain Dump")
INPUTS = ("Question", "Grocery list", "Task notes")
END_DATE = date(2026, 11, 12)
# Hypothetical rates per million tokens, used only to illustrate cost.
INPUT_RATE = Decimal("0.15")
OUTPUT_RATE = Decimal("0.60")


def sample_requests(days):
    rng = Random(20261112)
    rows = []
    for offset in range(30):
        day = END_DATE - timedelta(days=29 - offset)
        for _ in range(rng.randint(14, 32)):
            feature = rng.choices(range(3), weights=(6, 3, 2))[0]
            input_tokens = rng.randint(60, 230) + (140 if feature == 2 else 0)
            success = rng.random() > (0.03 + feature * 0.02)
            output_tokens = rng.randint(30, 120) + feature * 20 if success else 0
            latency = 180 + 3 * input_tokens + 5 * output_tokens + rng.randint(0, 270)
            if not success:
                latency += 900
            if day > END_DATE - timedelta(days=days):
                rows.append({
                    "day": day, "feature": FEATURES[feature], "input": INPUTS[feature],
                    "latency": latency, "success": success,
                    "cost": (input_tokens * INPUT_RATE + output_tokens * OUTPUT_RATE) / 1_000_000,
                })
    return rows


def summarize(rows):
    latency = [row["latency"] for row in rows]
    cost = sum(row["cost"] for row in rows)
    failures = sum(not row["success"] for row in rows)
    return {
        "count": len(rows), "mean_latency": mean(latency) / 1000,
        "p95": quantiles(latency, n=20, method="inclusive")[-1] / 1000,
        "failure_rate": 100 * failures / len(rows), "cost": cost,
        "cost_per_thousand": 1000 * cost / len(rows),
    }


@login_required
@require_safe
@never_cache
def dashboard(request):
    days = 7 if request.GET.get("days") == "7" else 30
    rows = sample_requests(days)
    overall = summarize(rows)
    features = [
        {"label": feature, **summarize([row for row in rows if row["feature"] == feature])}
        for feature in FEATURES
    ]
    daily_counts = Counter(row["day"] for row in rows)
    peak_day = max(sorted(daily_counts), key=daily_counts.get)
    peak = daily_counts[peak_day]
    daily = [
        {"day": day, "count": count, "bar": 100 * count / peak}
        for day, count in sorted(daily_counts.items())
    ]
    latency_limit = ceil(max(max(feature["mean_latency"], feature["p95"]) for feature in features))
    for feature, input_type in zip(features, INPUTS):
        feature["mean_position"] = 100 * feature["mean_latency"] / latency_limit
        feature["p95_position"] = 100 * feature["p95"] / latency_limit
        feature["input"] = input_type
        feature["share"] = 100 * feature["count"] / overall["count"]
        feature["cost_share"] = 100 * feature["cost"] / overall["cost"]
    return render(request, "analytics/dashboard.html", {
        "days": days, "overall": overall, "features": features, "daily": daily,
        "start": daily[0]["day"], "end": END_DATE,
        "latency_limit": latency_limit, "latency_midpoint": latency_limit / 2,
        "peak": peak, "peak_day": peak_day, "input_rate": INPUT_RATE, "output_rate": OUTPUT_RATE,
    })
