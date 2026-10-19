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
import shutil
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "hestia_config.settings.development")
os.environ.setdefault("SECRET_KEY", secrets.token_urlsafe(48))
os.environ.setdefault("HF_HOME", str(ROOT / "model_cache" / "huggingface"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2-0.5B-Instruct")
    parser.add_argument("--visual-fixtures", action="store_true", help="Render private HTML snapshots for desktop/mobile visual QA")
    args = parser.parse_args()
    print("Starting isolated real-model UI smoke check", flush=True)
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
    print("In-memory database ready; generating with local weights", flush=True)
    setup_test_environment()
    user = get_user_model().objects.create_user(username="p4-integration-check")
    workspace = Workspace.objects.create(name="P4 isolated test household")
    membership = Membership.objects.create(user=user, workspace=workspace, display_name="P4 test member")
    client = Client(enforce_csrf_checks=True)
    client.force_login(user)
    url = reverse("ai_tasks:brain-dump")
    page = client.get(url)
    assert page.status_code == 200
    snapshots = {"input": page.content}
    csrf = client.cookies["csrftoken"].value
    start = time.perf_counter()
    response = client.post(url, {"action": "generate", "workspace": workspace.pk,
        "text": "Guests are coming tomorrow. The kitchen is messy, we need groceries, and the bathroom tap is leaking badly.",
        "csrfmiddlewaretoken": csrf})
    elapsed = time.perf_counter() - start
    assert response.status_code == 200 and "review" in response.context, "Real model did not produce reviewable tasks"
    assert "Demo mode:" not in response.content.decode()
    assert Task.objects.count() == 0
    print("Real suggestions ready; checking edit/remove/confirmation", flush=True)
    snapshots["review"] = response.content
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
    snapshots["confirmation-required"] = unconfirmed.content
    data["confirm"] = "on"
    saved = client.post(url, data)
    assert saved.status_code == 302
    assert Task.objects.count() == count - 1
    assert Task.objects.filter(workspace=workspace, created_by_membership=membership).count() == count - 1
    task = Task.objects.get(title="Reviewed kitchen task")
    assert task.priority == "HIGH" and task.task_type == "CHORE"
    assert task.description == "Edited after real local inference."
    snapshots["saved"] = client.get(saved.url).content
    detail = client.get(task.get_absolute_url())
    assert detail.status_code == 200 and b"Create an AI action plan" in detail.content
    snapshots["task-detail"] = detail.content
    plan_url = reverse("workflows:task-action-plan", args=[task.pk])
    print("Approved tasks saved; checking disclosed Groq HTTP fixture", flush=True)
    settings.GROQ_API_KEY = "test-only-not-a-real-key"
    settings.GROQ_MODEL = "openai/gpt-oss-20b"
    from django.core.cache import cache
    cache.clear()
    plan_fixture = {"summary": "Clean the kitchen surfaces before guests arrive.",
        "steps": [{"title": "Clear the counters", "description": "Put away loose items."},
                  {"title": "Wipe the counters", "description": "Use a cleaner appropriate for the surface."}],
        "supplies": ["Cleaning cloth"], "cautions": ["Follow the cleaner's label instructions."]}
    provider_response = Mock(status_code=200)
    provider_response.json.return_value = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps(plan_fixture)}}]}
    with patch("workflows.action_plans.requests.post", return_value=provider_response) as provider:
        disclosure = client.get(plan_url)
        assert disclosure.status_code == 200 and not provider.called
        snapshots["action-plan-disclosure"] = disclosure.content
        planned = client.post(plan_url, {"csrfmiddlewaretoken": csrf})
        assert planned.status_code == 200 and b"Clear the counters" in planned.content
        assert provider.call_count == 1
    assert Task.objects.count() == count - 1
    task.refresh_from_db()
    assert task.description == "Edited after real local inference."
    snapshots["action-plan-preview"] = planned.content
    client.post(url, data)
    assert Task.objects.count() == count - 1
    evidence = {"model": "Qwen/Qwen2-0.5B-Instruct", "shot_mode": "many",
        "real_inference": True, "database": "temporary in-memory SQLite",
        "csrf_checks": True, "generation_with_load_seconds": round(elapsed, 3),
        "suggestions": count, "tasks_after_generation": 0, "tasks_without_confirmation": 0,
        "removed": 1, "saved_tasks": count - 1, "protected_attribution_verified": True,
        "edits_verified": True, "replay_no_extra_writes": True,
        "saved_task_action_plan_link": True, "plan_get_does_not_call_provider": True,
        "explicit_plan_post_verified": True, "external_http_mocked": True,
        "plan_does_not_change_tasks": True,
        "note": "Real local inference; Groq HTTP response is a labeled deterministic fixture. No live external API call or real key used."}
    if args.visual_fixtures:
        preview = ROOT / ".local-backups/p4-visual-qa"
        preview.mkdir(parents=True, exist_ok=True)
        shutil.copytree(ROOT / "static files/css", preview / "static/css", dirs_exist_ok=True)
        shutil.copytree(ROOT / "static files/images", preview / "static/images", dirs_exist_ok=True)
        for name, html in snapshots.items():
            text = html.decode("utf-8").replace('"/static/', '"static/')
            text = text.replace("<body>", '<body><p style="margin:0;padding:8px;background:#fff4d0;color:#3c3210">P4 visual QA: fictional household, real local suggestions, external plan fixture; static snapshot.</p>')
            (preview / f"{name}.html").write_text(text, encoding="utf-8")
        print("Private visual snapshots:", preview, flush=True)
    destination = ROOT / "a6_results/person4_django_integration.json"
    destination.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2), flush=True)


if __name__ == "__main__":
    main()
