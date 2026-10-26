# Step 2.5: local/API cost analysis

Validated 90 workload-aligned daily cost comparisons. API rows reuse one comparable hosted model; this is not measured quality equivalence or 15 exact-model API quotes.

API is cheaper in 90/90 cases; local in 0/90; ties 0.

## Workload, rates and scope

Both tables use one request/user/day, 256 input tokens and 500 output tokens, USD/day, and assumptions ID `hestia-a7-256in-500out-r1-inference-only-v1`. Person 3 uses one comparable `meta-llama/Llama-3.1-8B-Instruct` through Novita/Hugging Face for every local roster model. Reported October 23 catalog rates are $0.02/million input and $0.05/million output tokens, or $0.03012 per 1,000 requests. These supplied historical rates are scenario inputs, not newly verified live quotes or 15 distinct exact-model offers. Holding the external instruction service fixed lets each local alternative be compared against the same API rate. This does not establish size-matched or measured quality equivalence.

Local hosting includes GPU pod compute, disk and a colocated thin handler. API includes token charges and a separate Runpod 2-vCPU gateway with disk ($1.986667/day/replica). Gateway capacity of 50 requests/s is assumed, using shared utilization/peak/service factors. Both exclude the common Django/frontend/database baseline, egress, tax, labor, monitoring and redundancy. Local RTX3090 costs $0.50/hour plus disk under Person 2’s assumptions. Four throughput anchors are measured on T4; eleven are parameter-based estimates. T4-to-3090 capacity transfer is unvalidated. This is inference-tier planning cost, not production TCO.

| DAU | Local daily cost range across 15 alternatives | API daily cost (one comparable) |
|---|---|---|
| 1,000 | $12.333333–$37.000000 | $2.016787 |
| 10,000 | $49.333333–$333.000000 | $2.287867 |
| 100,000 | $431.666667–$3,268.333333 | $4.998667 |
| 1,000,000 | $4,255.000000–$32,671.000000 | $32.106667 |
| 10,000,000 | $42,513.000000–$326,697.666667 | $321.066667 |
| 100,000,000 | $425,093.000000–$3,266,865.666667 | $3,204.706667 |

## Required analysis answers

1. Local is cheaper at none of the six tested traffic levels for any of the 15 alternatives under these supplied assumptions.
2. API is cheaper at all six levels (1k, 10k, 100k, 1m, 10m, 100m DAU). The 15 API alternatives tie because they use the same hosted model and rates.
3. There are 0 observed cheaper-option changes between adjacent levels. No exact DAU crossover is supported. Present costs favor API from launch through the modeled scale; switch toward local only after revised rates/capacity show sustained savings and equivalent task quality, latency and availability. Keep API overflow for temporary peaks, subject to budget and quotas.

The hosted 8B candidate has not run the shared prompts. Price similarity does not establish quality equivalence; a cheap unqualified model cannot replace a qualified route. Huge calculated local fleets and API loads do not establish actual inventory or provider quota availability. Do not sum the 15 mutually exclusive local alternatives as one fleet.

## Separate price sensitivity

`api_rate_frontier.csv` and its figure retain an explicitly zero-gateway sensitivity case. They are not the paired comparison above. For D users, r requests/user, local cost L/day, gateway A/day and input/output rates pi/po in USD per million tokens:

`API/day = A + D*r*(256*pi + 500*po)/1,000,000`.

`b = po + (256/500)*pi; b_break_even = (L-A)*1,000,000/(D*r*500)`.

Local is cheaper above this price threshold; API below it, conditional on comparable quality/scope. Replica ceilings can cause multiple crossings; use all paired points rather than extrapolating one universal break-even.
