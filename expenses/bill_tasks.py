"""Keep one household task aligned with a recurring bill's upcoming due date."""
from datetime import datetime, time
from django.db import transaction
from django.db.models import Max
from workflows.models import Task, TaskOccurrence
from .insights import household_zone


@transaction.atomic
def sync_bill_task(bill, *, recorded=False):
    # Lock the bill so concurrent edits cannot create two reminder tasks.
    bill = type(bill).objects.select_for_update().select_related('workspace', 'paid_by').get(pk=bill.pk)
    task = bill.task
    if task is None:
        title = 'Pay ' + bill.title
        if Task.objects.filter(workspace=bill.workspace, title=title).exists():
            title += f' ({bill.pk})'
        task = Task.objects.create(workspace=bill.workspace, title=title,
            task_type=Task.TaskType.DEADLINE, priority=Task.Priority.HIGH,
            created_by_membership=bill.created_by)
        bill.task = task
        bill.save(update_fields=['task'])
    task.description = (f'Recurring bill: {bill.title}. Expected amount: ${bill.amount_cents / 100:.2f}. '
                        f'Usual payer: {bill.paid_by.display_name}. Record the actual bill in Expenses; '
                        'completing this reminder does not record a charge.')
    task.recurrence_rule = {'monthly':'FREQ=MONTHLY', 'weekly':'FREQ=WEEKLY', 'yearly':'FREQ=YEARLY'}[bill.frequency]
    task.save(update_fields=['description', 'recurrence_rule'])
    occurrence = task.occurrences.order_by('-sequence').first()
    if recorded:
        if occurrence:
            occurrence.state = TaskOccurrence.OccurrenceState.REPORTED_COMPLETE
            occurrence.save(update_fields=['state'])
        return task
    if occurrence is None or occurrence.state == TaskOccurrence.OccurrenceState.REPORTED_COMPLETE:
        sequence = (task.occurrences.aggregate(value=Max('sequence'))['value'] or 0) + 1
        occurrence = TaskOccurrence(task=task, sequence=sequence)
    occurrence.due_at = datetime.combine(bill.next_due, time(12), tzinfo=household_zone(bill.workspace))
    occurrence.state = TaskOccurrence.OccurrenceState.OPEN if bill.active else TaskOccurrence.OccurrenceState.CANCELLED
    occurrence.save()
    return task
