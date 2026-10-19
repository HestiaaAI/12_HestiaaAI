# Part 3 — P4: Local model vs paid API

Pricing checked October 18, 2026. These are transparent planning estimates, not
paid API experiments or proof that different-sized models have equal quality.
P4's historical CPU findings are in `benchmark_summary.md`; the completed 7–14B
GPU results are in [large-model-findings.md](large-model-findings.md) and the
[32-run CSV](../../a6_results/person4_large/person4_large_results.csv).

## Workload and cost assumptions

Assume 10,000 daily users, two extractions per user per day, 800 input tokens per
extraction (including instructions/examples) and 220 output tokens. That is
20,000 requests, 16M input tokens, and 4.4M output tokens per day. Actual prompt
length varies by shot mode; 800 is a planning scenario, not a measured average.
Thirty days gives 600,000 requests, 480M input and 132M output tokens.

Groq's published GPT-OSS 20B prices are $0.075/M input tokens and $0.30/M output
tokens. GPT-OSS 120B is $0.15/M input and $0.60/M output. These are public text
inference price references, not the team's selected Person 3 provider or a claim
of equivalence to the three sub-billion local models.
[Source: Groq supported models](https://console.groq.com/docs/models).

| Option | Calculation | Estimated USD |
| --- | --- | ---: |
| API 20B, per extraction | (800 × 0.075 + 220 × 0.30) / 1,000,000 | $0.000126 |
| API 20B, daily | 16 × 0.075 + 4.4 × 0.30 | $2.52 |
| API 20B, 30 days | 480 × 0.075 + 132 × 0.30 | $75.60 |
| API 120B, 30 days | 480 × 0.15 + 132 × 0.60 | $151.20 |
| Example RTX 3090 always on | $0.50/hour × 24 × 30 | $360.00 |
| Example RTX 4090 always on | $0.89/hour × 24 × 30 | $640.80 |

Runpod's displayed Pod configurations list RTX 3090 (24 GB VRAM, 125 GB host RAM,
16 vCPUs) at $0.50/hour and RTX 4090 (24 GB VRAM, 41 GB host RAM, 6 vCPUs) at
$0.89/hour. They are example offers, not quotes for the assignment's exact
16-core/64-GB/1-TB configuration. Availability, storage, network, replicas,
monitoring, application hosting, and engineering are additional considerations.
[Source: Runpod pricing](https://www.runpod.io/pricing).

Free tiers and student credits can reduce classroom costs, but rate limits and
expiry make them unsuitable as the only 10,000-user capacity plan. Cached input
discounts, batching, tax, retries and reasoning tokens are omitted. Include all
billed tokens in a real budget. We made no paid API calls for this comparison.

## When a local server is acceptable

Local inference can fit a classroom demonstration, an already-owned machine,
steady predictable demand, offline operation, or a documented requirement to
keep data on infrastructure controlled by the team. Existing hardware has a
marginal electricity cost rather than a new cloud rental bill, but still needs
maintenance and capacity planning. Local inference itself has no per-token bill.

For the assignment's hypothetical 16-core CPU, GPU, 64 GB RAM, and 1 TB disk,
specify the GPU model and **VRAM**: “16-core GPU” alone does not describe model
capacity. Approximate unquantized weights consume 4 bytes/parameter in FP32 and
2 bytes in FP16/BF16; a 7B model is about 28/14 GB, a 14B model about 56/28 GB.
Runtime activations, KV cache, Python, concurrent requests and the OS need extra
memory. A 14B FP16 model therefore exceeds a single 24-GB GPU before overhead.
Four-bit weights are about 0.5 byte/parameter before quantization metadata, but
require supported kernels and a separate quality/latency evaluation. Host RAM is
not interchangeable with GPU VRAM; disk capacity does not make inference fast.

The earlier small-model runs used CPU FP32 on approximately 15.5 GiB RAM.
P4 has now also measured Falcon3-7B and three 14B candidates on a Colab Tesla T4
with NF4 weights and FP32 computation/non-quantized modules. Qwen2.5-14B passed
the shared schema in 8/8 cases, averaged 20.778 seconds of generation, and scored
9.5/10 in assistant-assisted content review. Qwen3-14B also passed 8/8, averaged
21.801 seconds, and scored 9.25/10. Falcon passed 7/8; Phi passed 3/8 and had
schema mismatches/truncation under the shared 220-token cap. Human review remains
necessary even for valid JSON. These are two fixed inputs per model, not a
production quality or load test; speed comparisons with CPU/native runs are
not controlled. Main PR #31 uses a different balanced 15-model selection;
P1/the team decides whether to extend that analysis with these above-10B runs.

The Qwen2.5-14B last-case peak allocated VRAM was 12.751 GiB on the 14.563-GiB
T4; this field is not an aggregate maximum over every case. Quantization made
this test feasible, but does not establish the capacity of the hypothetical
server. Colab is cloud-hosted model inference, not proof of on-premise/offline
privacy. Only the fixed synthetic test paragraphs were used.

## When an API is preferable

At this illustrative workload, $75.60/month in tokens is below a continuously
rented $360/month GPU, before either option's common Django costs. APIs are
attractive for spiky demand, quick rollout, stronger-model quality, and avoiding
model loading/serving operations, provided acceptable privacy terms, rate limits,
latency and provider reliability are established. A published model size alone
does not prove comparable extraction quality; rerun the same prompts on any
candidate paid model before selecting it.

Using the 20B price example, a $12/day local rental equals token spending at about
95,238 extractions/day: 12 / 0.000126. This is a **billing-only** break-even. It
does not show that one GPU can serve that workload. At 20,000/day, average arrival
rate is 0.2315 requests/second. If local measured mean generation time is L
seconds, serialized service needs at least 0.2315 × L continuously busy workers
before prompt processing, peak headroom and latency constraints. At five times
average peak demand, multiply that by five. Use a production inference server,
queue, bounded concurrency and a real load test rather than running many Django
workers that each load an independent model.

For scale only, applying the observed Qwen2.5-14B generation mean to 20,000
requests gives 20,000 × 20.778 / 3,600 = **115.43 serialized GPU-hours/day**,
or **4.81 fully occupied T4 equivalents** before peak headroom. This is arithmetic
on a two-input sample, not a demonstrated serving capacity: the measured token
counts differ from the planning 800/220 scenario. Batching, prompt processing,
concurrency, model loading and end-to-end latency need an actual serving test.
Five Django workers do not turn one T4 into five independent GPU replicas.

## Hybrid potential

Use the local model to extract ordinary household tasks. Validate output and
require user review; reserve external AI for an explicitly requested breakdown
or a user-approved retry when local extraction fails. Never send raw household
input to an external provider silently. A quality gate can detect malformed
schema but cannot reliably detect all semantic mistakes; do not treat it as a
calibrated model-confidence score.

Example: 20% of the 20,000 daily requests use API extraction, and 10% request a
breakdown costing 300 input/600 output tokens. API extraction costs $0.504/day;
2,000 breakdowns cost (0.6 × 0.075 + 1.2 × 0.30) = $0.405/day. Combined external
cost is $0.909/day, or $27.27/30 days, **plus local hosting**. Adding a rented
$360/month GPU totals $387.27, which exceeds the $75.60 all-API extraction-only
scenario; those workloads differ because the hybrid also includes breakdowns.
Including the same breakdown volume in all-API yields $87.75/month. Hybrid is
therefore not automatically cheaper; it can make sense with already-owned local
capacity, privacy constraints, sustained utilization, or expensive API models.

The merged implementation reaches Person 3's Groq action-plan feature from a
saved task's detail page, after Brain Dump review and confirmation. A separate
disclosed POST sends the saved task fields and returns an unsaved plan preview.
P4's earlier pre-save callable remains an optional, disabled extension and is
not needed for this supported flow. Private Groq configuration is required for
live use; Person 3's live-call evidence is stored separately. P4's combined-path
test mocks the external HTTP response. The prices above remain planning estimates,
not P4 measurements of paid-provider quality or latency.
