"""Run `python -m workflows.forms_demo` for an isolated, disposable UI preview.

Uses a temporary SQLite database and a generated local login. It never reads or
writes application rows in the normal development or shared staging database.
"""
import os
from pathlib import Path
import secrets
from tempfile import TemporaryDirectory


def main():
    os.environ["DJANGO_SETTINGS_MODULE"] = "workflows.forms_preview_settings"
    from django.conf import settings

    with TemporaryDirectory(prefix="hestia-forms-") as directory:
        settings.DATABASES = {"default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": Path(directory) / "preview.sqlite3",
        }}
        import django
        django.setup()
        from django.contrib.auth import get_user_model
        from django.core.management import call_command
        from django.db import connections
        from allauth.account.models import EmailAddress
        from households.models import Membership, Workspace

        call_command("migrate", interactive=False, verbosity=0)
        call_command("seed_template_demo", verbosity=0)
        password = secrets.token_urlsafe(18)
        user = get_user_model().objects.create_user(
            username="forms-preview", email="forms-preview@example.test", password=password
        )
        EmailAddress.objects.create(user=user, email=user.email, verified=True, primary=True)
        workspace = Workspace.objects.get(name="Hestia demo household")
        Membership.objects.create(workspace=workspace, user=user, display_name="Preview member")
        print("\nForms preview: http://127.0.0.1:8015/tasks/manage/", flush=True)
        print(f"Email: {user.email}\nTemporary password: {password}\n", flush=True)
        print("Local demo only. Ctrl+C stops the server and discards its data.", flush=True)
        try:
            call_command("runserver", "127.0.0.1:8015", use_reloader=False)
        finally:
            connections.close_all()


if __name__ == "__main__":
    main()
