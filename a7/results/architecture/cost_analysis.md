# Step 2.5 — cost comparison and conditional switching thresholds

All 90 local rows from Person 2 are available. The 90 API rows from Person 3 are
not supplied, so an actual cheaper option or observed DAU crossover cannot yet be
reported. The completed `api_rate_frontier.csv` gives a price threshold for each
of the 15 models at each of the six required traffic levels without inventing API
prices or a provider/model mapping.

## Workload and scope

Keep Person 2's assumptions ID `hestia-a7-256in-500out-r1-inference-only-v1`:
one request/user/day, 256 input tokens and 500 output tokens. These are future
workload assumptions, not observed average benchmark lengths. The local estimate
includes GPU Pod compute, per-replica disk and a co-hosted thin handler. It excludes
the common Django/frontend/database baseline and the other explicitly excluded
items in `a7/person2/cost_assumptions.json`. API gateway compute/storage must be
included on the API side; a shared assumptions ID alone does not establish matching
scope, so the actual cost components must also be reviewed.

Person 2's advertised RTX 3090 rate of $0.50/hour, 24 GB VRAM, 125 GB RAM and
16 vCPU is still shown on the [official pricing page](https://www.runpod.io/pricing)
when checked October 25, 2026. The [billing documentation](https://docs.runpod.io/pods/pricing)
lists running container and volume storage at $0.10/GB/month. These advertised
figures do not guarantee inventory, enterprise capacity or a deployment quote.
Person 2's throughput transfer from T4 to RTX 3090 is an explicit unvalidated
assumption; eleven of the fifteen rates are parameter-size proxies. Treat the
machine counts and costs as planning scenarios rather than measured production TCO.

## Conditional price frontier

Let D be daily users, r requests/user/day, A the API gateway's total daily cost,
and pi/po the API's input/output prices in USD per million tokens:

`API cost/day = A + D*r*(256*pi + 500*po)/1,000,000`.

Normalize to an output-equivalent blended rate `b = po + (256/500)*pi`.
For local cost L from the corresponding row, the tie price is:

`b_break_even = (L-A)*1,000,000/(D*r*500)`.

- Local is cheaper if `b > b_break_even`.
- API is cheaper if `b < b_break_even`.
- Equal values tie under the stated inclusion scope and quality equivalence.

The exported frontier explicitly assumes A=$0/day. This is an optimistic API
lower-bound cost case, not a claim that API infrastructure is free. Actual gateway
cost lowers the tie price. A negative threshold means gateway overhead alone
exceeds local cost; do not clip it to zero and conceal that result.

For Mistral-7B's local scenario, the threshold is $74 per million output-equivalent
tokens at 1,000 DAU (local $37/day), falling toward $62.1647 at 100 million DAU.
These are calculated thresholds, not API rate quotes. They illustrate that scaling
does not automatically make local cheaper: local replica count grows with load,
while API token charges also grow with load. Rounding/minimum replicas and actual
input/output prices determine whether any crossing exists.

## Required analysis answers

1. **At what scale is local cheaper?** For each model/traffic row, when the actual
   comparable API's blended rate exceeds that row's threshold after including its
   gateway cost. No measured scale can be named before the compatible API table arrives.
2. **At what scale is API cheaper?** When its complete daily charge lies below the
   corresponding local estimate. The zero-gateway CSV is only an optimistic API
   bound; prices below its threshold do not guarantee API is cheaper after gateway costs.
3. **When switch architecture?** Switch after sustained workload forecasts show
   sufficient savings to justify migration/operation effort and the target passes
   task-quality and queue-latency gates. Use budgeted API overflow for temporary
   spikes; verify provider quotas and planned GPU capacity. Neither the current
   batch-one timings nor very large calculated fleets establish production feasibility.

When `a7/results/api_costs.csv` arrives, `architecture_analysis.compare_costs`
validates all 90 paired workloads, compares full daily totals, and reports every
change in cheaper option between adjacent DAU levels. Those intervals bracket
crossovers; they do not establish an exact threshold between the six sampled loads.
