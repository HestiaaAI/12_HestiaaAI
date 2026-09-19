from django.core.management.base import BaseCommand
from django.db import transaction

from households.models import Workspace
from workflows.models import Task


class Command(BaseCommand):
    help = "Add fictional Section 3 demo tasks without changing existing tasks."

    @transaction.atomic
    def handle(self, *args, **options):
        workspace, _ = Workspace.objects.get_or_create(name="Hestia demo household")
        examples = [
            ("Plan the weekly groceries", "Check pantry staples and make a list for the week ahead.", "SHOPPING", "HIGH", "Kitchen", "Every Sunday"),
            ("Take out the recycling", "Collect paper, cans, and bottles before the morning pickup.", "CHORE", "MEDIUM", "Garage", "Every Tuesday"),
            ("Replace the air filter", "Check the filter size and replace the hallway air filter.", "MAINTENANCE", "LOW", "Hallway", ""),
        ]
        created_count = 0
        for title, description, task_type, priority, location, recurrence in examples:
            _, created = Task.objects.get_or_create(
                workspace=workspace, title=title,
                defaults={"description": description, "task_type": task_type,
                          "priority": priority, "default_location": location,
                          "recurrence_rule": recurrence},
            )
            created_count += created
        self.stdout.write(self.style.SUCCESS(f"Created {created_count} fictional demo tasks."))
