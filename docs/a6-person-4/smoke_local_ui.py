"""Real local inference → review/edit/remove/confirm/save on an in-memory DB.

Run after installing root requirements. Does not patch inference or touch the
project database. Pass --model with a model ID or an existing local snapshot.
"""
import argparse
import json
import os
from pathlib import Path
import secrets
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hestia_config.settings.development")
os.environ.setdefault("SECRET_KEY", secrets.token_urlsafe(48))
os.environ.setdefault("HF_HOME", str(ROOT / "model_cache" / "huggingface"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2-0.5B-Instruct")
    args = parser.parse_args()
    import django
    from django.conf import settings
    settings.DATABASES["default"]["NAME"] = ":memory:"
    settings.ALLOWED_HOSTS = ["testserver"]
    settings.HESTIA_BRAIN_DUMP_BACKEND = "local"
    settings.HF_BRAIN_DUMP_MODEL = args.model
    settings.HF_BRAIN_DUMP_DEVICE = "cpu"
    settings.HF_BRAIN_DUMP_SHOT_MODE = "many"
    settings.HF_BRAIN_DUMP_MAX_NEW_TOKENS = 220
    django.setup()
    import torch
    torch.set_num_threads(4)
    from django.core.management import call_command
    from django.contrib.auth import get_user_model
    from django.test import Client
    from django.test.utils import setup_test_environment
    from django.urls import reverse
    from households.models import Membership, Workspace
    from workflows.models import Task
    call_command("migrate", verbosity=0)
    setup_test_environment()
    user = get_user_model().objects.create_user(username="p4-integration-check")
    workspace = Workspace.objects.create(name="P4 isolated test household")
    membership = Membership.objects.create(user=user, workspace=workspace, display_name="P4 test member")
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    url = reverse("ai_tasks:brain-dump")
    page = client.get(url)
    assert page.status_code == 200
    csrf = client.cookies["csrftoken"].value
    start = time.perf_counter()
    response = client.post(url, {"action": "generate", "workspace": workspace.pk,
        "text": "Guests are coming tomorrow. The kitchen is messy, we need groceries, and the bathroom tap is leaking badly.",
        "csrfmiddlewaretoken": csrf})
    elapsed = time.perf_counter() - start
    assert response.status_code == 200 and "review" in response.context, "Real model did not produce reviewable tasks"
    assert "Demo mode:" not in response.content.decode()
    assert Task.objects.count() == 0
    review = response.context["review"]
    count = len(review.forms)
    assert count >= 2, "Smoke case requires multiple generated tasks"
    data = {"action": "save", "draft_token": response.context["draft_token"],
            "form-TOTAL_FORMS": count, "form-INITIAL_FORMS": count,
            "form-MIN_NUM_FORMS": 0, "form-MAX_NUM_FORMS": 20, "csrfmiddlewaretoken": csrf}
    for index, form in enumerate(review.forms):
        for key, value in form.initial.items():
            data[f"form-{index}-{key}"] = value
    data["form-0-title"] = "Reviewed kitchen task"
    data["form-0-priority"] = "HIGH"
    data["form-0-task_type"] = "CHORE"
    data["form-0-description"] = "Edited after real local inference."
    data["form-1-DELETE"] = "on"
    unconfirmed = client.post(url, data)
    assert unconfirmed.status_code == 200 and Task.objects.count() == 0
    data["confirm"] = "on"
    saved = client.post(url, data)
    assert saved.status_code == 302
    assert Task.objects.count() == count - 1
    assert Task.objects.filter(workspace=workspace, created_by_membership=membership).count() == count - 1
    task = Task.objects.get(title="Reviewed kitchen task")
    assert task.priority == "HIGH" and task.task_type == "CHORE"
    assert task.description == "Edited after real local inference."
    client.post(url, data)
    assert Task.objects.count() == count - 1
    evidence = {"model": "Qwen/Qwen2-0.5B-Instruct", "shot_mode": "many",
        "real_inference": True, "database": "temporary in-memory SQLite",
        "csrf_checks": True, "generation_with_load_seconds": round(elapsed, 3),
        "suggestions": count, "tasks_after_generation": 0, "tasks_without_confirmation": 0,
        "removed": 1, "saved_tasks": count - 1, "protected_attribution_verified": True,
        "edits_verified": True, "replay_no_extra_writes": True,
        "note": "Configured local snapshot; no inference mocks and no external API calls."}
    destination = ROOT / "a6_results/person4_django_integration.json"
    destination.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2), flush=True)


if __name__ == "__main__":
    main()
