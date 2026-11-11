from django.core.management.base import BaseCommand

from households.models import Workspace
from inventory.expiry import expiring_batches, household_today


class Command(BaseCommand):
    help = "Report active grocery batches that are overdue or expire within three days."

    def handle(self, *args, **options):
        for workspace in Workspace.objects.iterator():
            today = household_today(workspace)
            batches = expiring_batches(workspace, today)
            overdue = batches.filter(expires_on__lt=today).count()
            soon = batches.filter(expires_on__gte=today).count()
            if overdue or soon:
                self.stdout.write(f"Household {workspace.pk}: {overdue} past date, {soon} due soon")
