"""Validate the exported larger-model evidence without inventing review scores."""
import argparse
import csv
import importlib.util
import json
import math
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def verify(folder):
    spec = importlib.util.spec_from_file_location(
        "p4_large_runner", ROOT / "llm-test/person4_large_benchmark.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    assert (folder / "support/team_contract.py").is_file(), "Missing exported contract"
    team = runner.shared_contract(folder / "support")
    with (folder / "person4_large_results.csv").open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        assert reader.fieldnames == team.CSV_FIELDS, "CSV columns changed"
        rows = list(reader)
    metadata = json.loads((folder / "person4_large_metadata.json").read_text(encoding="utf-8"))
    expected = {(m, i, s) for m in runner.MODELS for i in team.TEST_INPUTS for s in team.SHOT_MODES}
    keys = [(r["model_id"], r["input_id"], r["shot_mode"]) for r in rows]
    assert len(keys) == len(set(keys)), "Duplicate generations"
    assert set(keys) == expected, f"Missing/unexpected generations: {set(keys) ^ expected}"
    assert metadata["contract_sha256"] == runner.CONTRACT_SHA256
    assert set(metadata["models"]) == set(runner.MODELS)
    for row in rows:
        for key in ("load_seconds", "generation_seconds"):
            value = float(row[key])
            assert math.isfinite(value) and value > 0, f"Invalid timing: {row['model_id']}/{key}"
        assert 0 < int(row["output_tokens"]) <= 220
        try:
            errors = team.validate_payload(team.extract_json(row["raw_output"]))
        except (ValueError, TypeError) as exc:
            errors = [str(exc)]
        assert row["schema_valid"] == str(not errors), "Stored schema result differs from shared validator"
        assert row["validation_errors"] == " | ".join(errors)
        if row["quality_score_0_to_10"]:
            score = float(row["quality_score_0_to_10"])
            assert math.isfinite(score) and 0 <= score <= 10
    for model in runner.MODELS:
        detail = metadata["models"][model]
        assert detail["status"] == "complete" and detail["completed_generations"] == 8
        assert len(detail["revision"]) == 40
        selected = [r for r in rows if r["model_id"] == model]
        print(model, "runs=", len(selected), "schema_valid=",
              sum(r["schema_valid"] == "True" for r in selected),
              "mean_generation_s=", round(sum(float(r["generation_seconds"]) for r in selected) / 8, 3),
              "reviewed=", sum(bool(r["quality_score_0_to_10"]) for r in selected))
    raw_path = folder / 'person4_large_raw_results.csv'
    if raw_path.exists():
        with raw_path.open(encoding='utf-8',newline='') as f:
            raw_rows = list(csv.DictReader(f))
        retained = [k for k in team.CSV_FIELDS if k not in ('quality_score_0_to_10','review_notes')]
        assert [{k:r[k] for k in retained} for r in rows] == [{k:r[k] for k in retained} for r in raw_rows], 'Review changed generation evidence'
        audit = json.loads((folder/'person4_large_review_audit.json').read_text(encoding='utf-8'))
        assert audit['raw_csv_sha256'] == hashlib.sha256(raw_path.read_bytes()).hexdigest()
        assert audit['reviewed_csv_sha256'] == hashlib.sha256((folder/'person4_large_results.csv').read_bytes()).hexdigest()
        assert audit['generation_metadata_sha256'] == hashlib.sha256((folder/'person4_large_run_metadata.json').read_bytes()).hexdigest()
        assert audit['reviewed_responses'] == len(audit['reviews']) == 32
        for row, review in zip(rows,audit['reviews']):
            assert (row['model_id'],row['input_id'],row['shot_mode']) == (review['model_id'],review['input_id'],review['shot_mode'])
            assert sum(review['points_E_T_P_C_F']) == float(row['quality_score_0_to_10'])
            assert review['raw_output_sha256'] == hashlib.sha256(row['raw_output'].encode('utf-8')).hexdigest()
    reviewed = sum(bool(r["quality_score_0_to_10"]) for r in rows)
    print(f"Verified 32 unique actual generations; {reviewed}/32 have recorded content reviews.")
    return rows, metadata


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", type=Path, default=ROOT / "a6_results/person4_large")
    verify(parser.parse_args().folder)
