from datetime import timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone

from inventory.models import GroceryBatch


SOON_DAYS = 3


def household_today(workspace, now=None):
    try:
        zone = ZoneInfo(workspace.timezone)
    except (ValueError, ZoneInfoNotFoundError):
        zone = timezone.get_default_timezone()
    return timezone.localdate(now, zone)


def expiring_batches(workspace, today):
    return GroceryBatch.objects.filter(
        workspace=workspace,
        state=GroceryBatch.State.ACTIVE,
        expires_on__lte=today + timedelta(days=SOON_DAYS),
    ).order_by("expires_on", "pk")


def suggestion_inputs(workspace, today):
    return list(expiring_batches(workspace, today).filter(expires_on__gte=today)[:6])


def batch_snapshot(batches):
    return [[batch.pk, batch.name, str(batch.quantity), batch.unit,
             batch.storage, batch.expires_on.isoformat()] for batch in batches]
