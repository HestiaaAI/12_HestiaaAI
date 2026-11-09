"""Join reviewed answers to the measured requests, retaining each complete hit list."""
import csv
import json
from collections import Counter
from pathlib import Path
from statistics import mean, median

from a8.corpus import STRATEGIES, load_queries
from a8.person2_experiments import read_rows
from a8.person3_experiments import OUT
from a8.retrieval import fingerprint

SIZES = ("small", "medium", "large")
FACTS = {q["id"]: q["required_facts"] for q in load_queries()}


def evidence_key(row):
    return fingerprint([row["query"], row["answer"], row["retrieved_chunks"]])


def evaluation_table(directory=OUT):
    directory = Path(directory)
    with (directory/"reviews.csv").open(encoding="utf-8") as file:
        records = list(csv.DictReader(file))
    reviews = {record["row_id"]: record for record in records}
    result = []
    for size in SIZES:
        rows = read_rows(directory/size/"rows.jsonl")
        expected = {f"{size}/full/{s}/{q}" for s in STRATEGIES for q in FACTS}
        if {r["row_id"] for r in rows} != expected:
            raise ValueError(f"Incomplete {size} matrix")
        for row in rows:
            review = reviews[row["row_id"]]
            if review["evidence_sha256"] != evidence_key(row):
                raise ValueError(f"Changed response or context for {row['row_id']}, review again")
            fact_count = len(FACTS[row["query_id"]])
            facts = [int(n) for n in review["matched_facts"].split()]
            deductions = int(review["unsupported_count"])
            if len(set(facts)) != len(facts) or any(n<1 or n>fact_count for n in facts) or deductions<0:
                raise ValueError(f"Invalid review: {row['row_id']}")
            result.append(dict(size=size, row_id=row["row_id"], embedding_model=row["embedding_model"],
                               dimension=row["embedding_dimension"], strategy=row["strategy"],
                               query_id=row["query_id"], query=row["query"], answer=row["answer"],
                               retrieved_context_quality=round(100*row["evidence_quote_coverage"],2),
                               first_support_rank=round(1/row["source_reciprocal_rank"]) if row["source_reciprocal_rank"] else None,
                               answer_quality=round(100*max(0,len(facts)-deductions)/fact_count,2),
                               retrieval_ms=row["retrieval_ms"], generation_ms=row["generation_ms"],
                               end_to_end_ms=row["end_to_end_ms"], notes=review["notes"],
                               retrieved_chunks=json.dumps(row["retrieved_chunks"],ensure_ascii=False)))
    if Counter(r["row_id"] for r in records) != Counter(r["row_id"] for r in result):
        raise ValueError("Duplicate, extra or missing reviews")
    return result


def summary(rows):
    for size in SIZES:
        part = [row for row in rows if row["size"] == size]
        yield dict(size=size, dimension=part[0]["dimension"], runs=len(part),
                   mean_context=mean(r["retrieved_context_quality"] for r in part),
                   mean_answer=mean(r["answer_quality"] for r in part),
                   rank_one=sum(r["first_support_rank"]==1 for r in part),
                   median_retrieval_ms=median(r["retrieval_ms"] for r in part),
                   median_request_ms=median(r["end_to_end_ms"] for r in part))


def export(rows, path):
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]),lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    rows = evaluation_table()
    export(rows, OUT/"evaluation.csv")
    export(list(summary(rows)), OUT/"comparison.csv")
