"""Measure real Ask Hestia page requests using a disposable SQLite database.

Run from the repository root: python -m a9.evaluate --phase after
The requested phase must be new to preserve existing evidence.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
from time import perf_counter

ROOT = Path(__file__).resolve().parent


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def evaluate(phase, baseline=False):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hestia_config.settings.development")
    from django.conf import settings

    # Override before opening connections. The user's database is never used.
    settings.DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": ":memory:"}}
    settings.ALLOWED_HOSTS = ["testserver"]
    settings.HF_ASK_HESTIA_DEVICE = "cpu"

    import django
    django.setup()
    from django.contrib.auth import get_user_model
    from django.core.management import call_command
    from django.test import Client
    from django.test.utils import setup_test_environment
    from django.urls import reverse
    import torch

    from workflows.services import ask_hestia as backend
    from unittest.mock import patch

    if baseline:
        from importlib.machinery import SourceFileLoader
        from importlib.util import module_from_spec, spec_from_loader
        snapshot = ROOT / "results" / "baseline" / "backend.py.txt"
        loader = SourceFileLoader("a9_baseline_backend", str(snapshot))
        backend = module_from_spec(spec_from_loader(loader.name, loader))
        loader.exec_module(backend)

    output = ROOT / "results" / phase
    if (output / "requests.jsonl").exists():
        raise ValueError(f"{output} already contains measured requests. Choose a new phase.")
    output.mkdir(parents=True, exist_ok=True)
    inputs_file = ROOT / "inputs.json"
    cases = json.loads(inputs_file.read_text(encoding="utf-8"))

    call_command("migrate", verbosity=0)
    setup_test_environment()
    user = get_user_model().objects.create_user(username="a9-evaluation", password=None)
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    url = reverse("ask-hestia")
    client.get(url)
    csrf_token = client.cookies["csrftoken"].value
    torch.set_num_threads(4)

    started = perf_counter()
    backend._index()
    tokenizer, model = backend._generator("cpu")
    try:
        backend._generate(cases[0]["question"], backend._retrieve(cases[0]["question"]))
    except backend.AskHestiaError:
        pass
    warmup_seconds = perf_counter() - started

    backend_source = Path(backend.__file__).read_bytes()
    manifest = {
        "backend_sha256": hashlib.sha256(backend_source).hexdigest(),
        "generator": backend.GENERATOR, "embedder": backend.EMBEDDER,
        "generator_revision": model.config._commit_hash,
        "embedding_revision": backend._index()[1].config._commit_hash,
        "chunking": getattr(backend, "CHUNKING_STRATEGY", "fixed"),
        "top_k": backend.TOP_K, "min_similarity": backend.MIN_SIMILARITY,
        "torch_threads": torch.get_num_threads(), "dtype": str(model.dtype), "device": "cpu",
        "warmup_seconds": warmup_seconds,
        "inputs_sha256": hashlib.sha256(inputs_file.read_bytes()).hexdigest(),
    }
    write_json(output / "manifest.json", manifest)
    (output / "backend.py.txt").write_bytes(backend_source)

    # Trace real calls. These wrappers call the original functions and model.
    original_retrieve = backend._retrieve
    original_generate = model.generate
    trace = {}

    def traced_retrieve(question):
        started = perf_counter()
        sources = original_retrieve(question)
        trace.update(sources=sources, retrieval_seconds=perf_counter() - started)
        return sources

    def traced_generate(*args, **kwargs):
        started = perf_counter()
        generated = original_generate(*args, **kwargs)
        length = kwargs["input_ids"].shape[1]
        trace.update(
            prompt=tokenizer.decode(kwargs["input_ids"][0], skip_special_tokens=False),
            model_seconds=perf_counter() - started,
            raw_answer=tokenizer.decode(generated[0, length:], skip_special_tokens=True),
            input_tokens=length, output_tokens=len(generated[0, length:]),
        )
        return generated

    with patch("workflows.ask_hestia_views.answer_question", backend.answer_question),          patch.object(backend, "_retrieve", traced_retrieve),          patch.object(model, "generate", traced_generate):
        for case in cases:
            trace = {}
            started = perf_counter()
            response = client.post(url, {"question": case["question"], "csrfmiddlewaretoken": csrf_token})
            elapsed = perf_counter() - started
            context = response.context
            row = {
                "id": case["id"], "question": case["question"],
                "expected_behavior": case["expected_behavior"],
                "http_status": response.status_code,
                "result": context.get("result"), "error": context.get("error"),
                "form_errors": context["form"].errors.get_json_data(),
                "request_seconds": elapsed, "trace": trace,
            }
            (output / (case["id"] + ".html")).write_bytes(response.content)
            with (output / "requests.jsonl").open("a", encoding="utf-8") as file:
                file.write(json.dumps(row, ensure_ascii=False) + "\n")
            visible = row["error"] or (row["result"] or {}).get("answer") or row["form_errors"]
            print(case["id"], round(elapsed, 3), visible, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--baseline", action="store_true", help="Replay the archived baseline service through the real page")
    arguments = parser.parse_args()
    if not arguments.phase.replace("-", "").replace("_", "").isalnum():
        parser.error("phase must contain only letters, numbers, hyphens and underscores")
    evaluate(arguments.phase, arguments.baseline)
