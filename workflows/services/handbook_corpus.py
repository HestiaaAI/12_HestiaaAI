"""Load the handbook and create topic-bounded chunks with source IDs."""

import argparse
from collections import defaultdict
from dataclasses import asdict, dataclass
from itertools import groupby
import json
from pathlib import Path
import re


DATA = Path(__file__).resolve().parent / "handbook_data"
STRATEGIES = ("fixed", "overlap", "hybrid")
DATASETS = ("small", "full")


def word_count(text):
    return len(re.findall(r"\b\w+(?:[-’']\w+)*\b", text))


@dataclass(frozen=True)
class Paragraph:
    id: str
    document: str
    section: str
    text: str


@dataclass(frozen=True)
class Chunk:
    id: str
    document: str
    section: str
    paragraph_ids: tuple[str, ...]
    text: str


def load_paragraphs(dataset="full", data_dir=DATA):
    """Read blank-line-separated prose blocks under each Markdown topic heading."""
    if dataset not in DATASETS:
        raise ValueError(f"Unknown dataset {dataset!r}; choose from {DATASETS}")
    data_dir = Path(data_dir)
    paragraphs = []
    for path in sorted((data_dir / "handbook").glob("*.md")):
        section = None
        number = 0
        for block in re.split(r"\n\s*\n", path.read_text(encoding="utf-8").strip()):
            if block.startswith("# "):
                continue
            if block.startswith("## "):
                section = block.removeprefix("## ")
                continue
            if section is None:
                raise ValueError(f"Paragraph without a topic heading in {path.name}")
            number += 1
            if dataset == "full" or number <= 3:
                paragraphs.append(Paragraph(f"{path.stem}-{number:02}", path.stem,
                                            section, " ".join(block.split())))
    if not paragraphs:
        raise ValueError(f"No handbook paragraphs found under {data_dir}")
    return paragraphs


def load_queries(data_dir=DATA):
    return json.loads((Path(data_dir) / "queries.json").read_text(encoding="utf-8"))


def pack_units(units, max_words):
    group = []
    total = 0
    for unit in units:
        count = word_count(unit[1])
        if group and total + count > max_words:
            yield group
            group, total = [], 0
        group.append(unit)
        total += count
    if group:
        yield group


def chunk_paragraphs(paragraphs, strategy):
    """Chunk in document order. Every chunk stays within one topic section."""
    if strategy not in STRATEGIES:
        raise ValueError(f"Unknown strategy {strategy!r}; choose from {STRATEGIES}")
    chunks = []
    sequence = defaultdict(int)
    for (document, section), section_paragraphs in groupby(
            paragraphs, key=lambda p: (p.document, p.section)):
        units = [(p.id, p.text) for p in section_paragraphs]
        separator = "\n\n"
        if strategy == "fixed":
            # The controlled handbook uses ordinary sentence-ending punctuation.
            sentences = ((pid, sentence) for pid, text in units
                         for sentence in re.split(r"(?<=[.!?])\s+", text))
            groups = pack_units(sentences, 140)
            separator = " "
        elif strategy == "overlap":
            # Window of two paragraphs, stride one. No redundant trailing singleton.
            groups = (units[start:start + 2] for start in range(max(1, len(units) - 1)))
        else:
            # Preserve paragraph units and pack consecutive units within the topic.
            groups = pack_units(units, 240)
        for group in groups:
            sequence[document] += 1
            chunks.append(Chunk(f"{strategy}-{document}-{sequence[document]:02}", document,
                                section, tuple(dict.fromkeys(pid for pid, _ in group)),
                                separator.join(text for _, text in group)))
    return chunks


def load_chunks(strategy, dataset="full", data_dir=DATA):
    return chunk_paragraphs(load_paragraphs(dataset, data_dir), strategy)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=DATASETS, default="full")
    parser.add_argument("--output-dir", type=Path, help="Optional folder for chunk JSON files")
    args = parser.parse_args()
    paragraphs = load_paragraphs(args.dataset)
    print(f"{args.dataset}: {len(paragraphs)} paragraphs, "
          f"{sum(word_count(p.text) for p in paragraphs)} words")
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
    for strategy in STRATEGIES:
        chunks = chunk_paragraphs(paragraphs, strategy)
        print(f"  {strategy}: {len(chunks)} chunks")
        if args.output_dir:
            path = args.output_dir / f"{args.dataset}-{strategy}.json"
            path.write_text(json.dumps([asdict(chunk) for chunk in chunks], indent=2,
                                       ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
