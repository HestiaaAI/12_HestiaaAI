"""Run a matched, timed A8 matrix. Invoke from the repository root."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path
from time import perf_counter

from a8.corpus import STRATEGIES, load_chunks, load_queries
from a8.generation import MODEL, REVISION, MAX_NEW_TOKENS, SYSTEM, generate_answer, load_generator
from a8.person2_experiments import environment, read_rows, write_json
from a8.retrieval import build_index, fingerprint, load_encoder, search, score_retrieval

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results" / "person3"
REVISIONS = {row["size"]: row["revision"] for row in json.loads(
    (ROOT / "results/person2/model_smoke_tests.json").read_text())}


def run(size, directory, scaling=False):
    import torch
    torch.set_num_threads(4)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    queries = load_queries()
    strategies = ("hybrid",) if scaling else STRATEGIES
    datasets = ("small", "full") if scaling else ("full",)
    jobs = {(d, s): load_chunks(s, d) for d in datasets for s in strategies}
    encoder = load_encoder(size, device="cpu", revision=REVISIONS[size])
    config = dict(encoder=encoder.a8_metadata, generator=MODEL, revision=REVISION, system=SYSTEM,
                  decoding="greedy, 1 beam, float32 CPU", max_new_tokens=MAX_NEW_TOKENS, top_k=3,
                  mode="scaling" if scaling else "matrix", query_digest=fingerprint(queries),
                  corpus_digest=fingerprint([[asdict(c) for c in cs] for cs in jobs.values()]),
                  generator_code=fingerprint((ROOT/"generation.py").read_text()),
                  environment=environment())
    manifest = directory/"manifest.json"
    if manifest.exists() and json.loads(manifest.read_text()) != config:
        raise ValueError("Run settings changed. Use a fresh output directory.")
    write_json(manifest, config)
    raw = directory/"rows.jsonl"
    seen = {r["row_id"] for r in read_rows(raw)}
    load_generator()
    for (dataset, strategy), chunks in jobs.items():
        index = build_index(chunks, encoder, encoder.a8_metadata)
        hits = search(index, queries[0]["query"], encoder)
        generate_answer(queries[0]["query"], hits)  # exclude warm-up and index builds
        for q in queries:
            row_id = "/".join((size, dataset, strategy, q["id"]))
            if row_id in seen:
                continue
            timings = {}
            start = perf_counter()
            hits = search(index, q["query"], encoder, top_k=3, timings=timings)
            retrieval_ms = (perf_counter()-start)*1000
            generated = generate_answer(q["query"], hits)
            latency = (perf_counter()-start)*1000
            row = dict(row_id=row_id, embedding_model=encoder.a8_metadata["model_id"],
                       embedding_dimension=encoder.a8_metadata["dimension"], generator=MODEL,
                       strategy=strategy, dataset=dataset, query_id=q["id"], query=q["query"],
                       retrieved_chunks=hits, retrieval_ms=retrieval_ms, end_to_end_ms=latency,
                       **timings, **generated, **score_retrieval(hits, q))
            with raw.open("a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False)+"\n")
            print(row_id, f"{latency/1000:.2f}s", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("size", choices=REVISIONS)
    parser.add_argument("--scaling", action="store_true")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    run(args.size, args.out or OUT/(args.size + ("-scaling" if args.scaling else "")), args.scaling)
