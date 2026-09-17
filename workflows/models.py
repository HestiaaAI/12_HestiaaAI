from django.db import models
from django.utils import timezone

from households.models import Membership, Workspace
from intake.models import SourceDocument
from inventory.models import Product, ShoppingListEntry


class Task(models.Model):
    """
    Represents a reusable responsibility, errand, appointment, or deadline.

    It connects work performed in a workspace with its creator, supporting
    documents, products, shopping entries, and scheduled occurrences.
    """

    class TaskType(models.TextChoices):
        CHORE = "CHORE", "Chore"
        APPOINTMENT = "APPOINTMENT", "Appointment"
        DEADLINE = "DEADLINE", "Deadline"
        ERRAND = "ERRAND", "Errand"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        SHOPPING = "SHOPPING", "Shopping"
        OTHER = "OTHER", "Other"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        URGENT = "URGENT", "Urgent"

    task_id = models.AutoField(primary_key=True)

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="tasks",
    )

    source_document = models.ForeignKey(
        SourceDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="generated_tasks",
    )

    created_by_membership = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tasks",
    )

    related_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="related_tasks",
    )

    related_shopping_list_entry = models.ForeignKey(
        ShoppingListEntry,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="related_tasks",
    )

    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)

    task_type = models.CharField(
        max_length=40,
        choices=TaskType.choices,
        default=TaskType.OTHER,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    recurrence_rule = models.CharField(max_length=255, blank=True)
    default_location = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            "-created_at",
            "title",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "title"],
                name="unique_task_title_per_workspace",
            )
        ]

    def __str__(self):
        return self.title


class TaskOccurrence(models.Model):
    """
    Represents one scheduled instance of a reusable task.

    It allows each occurrence to have its own schedule, due date, state,
    assignments, and lifecycle independently of other occurrences.
    """

    class OccurrenceState(models.TextChoices):
        OPEN = "OPEN", "Open"
        OFFER_PENDING = "OFFER_PENDING", "Offer pending"
        ASSIGNED = "ASSIGNED", "Assigned"
        IN_PROGRESS = "IN_PROGRESS", "In progress"
        REPORTED_COMPLETE = "REPORTED_COMPLETE", "Reported complete"
        SKIPPED = "SKIPPED", "Skipped"
        CANCELLED = "CANCELLED", "Cancelled"
        OVERDUE = "OVERDUE", "Overdue"

    task_occurrence_id = models.AutoField(primary_key=True)

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="occurrences",
    )

    sequence = models.PositiveIntegerField(default=1)

    scheduled_for = models.DateTimeField(
        null=True,
        blank=True,
    )
    due_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    state = models.CharField(
        max_length=30,
        choices=OccurrenceState.choices,
        default=OccurrenceState.OPEN,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = [
            "due_at",
            "task__title",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["task", "sequence"],
                name="unique_sequence_per_task",
            )
        ]

    def __str__(self):
        return f"{self.task.title} - occurrence {self.sequence}"


class Assignment(models.Model):
    """
    Represents one attempt to assign a task occurrence to a member.

    It records who proposed and received the assignment, its response
    state, response timestamps, and any reason for declining it.
    """

    class AssignmentState(models.TextChoices):
        OFFERED = "OFFERED", "Offered"
        ACCEPTED = "ACCEPTED", "Accepted"
        DECLINED = "DECLINED", "Declined"
        UNANSWERED = "UNANSWERED", "Unanswered"
        REASSIGNED = "REASSIGNED", "Reassigned"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    assignment_id = models.AutoField(primary_key=True)

    task_occurrence = models.ForeignKey(
        TaskOccurrence,
        on_delete=models.PROTECT,
        related_name="assignments",
    )

    proposed_by_membership = models.ForeignKey(
        Membership,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="proposed_assignments",
    )

    offered_to_membership = models.ForeignKey(
        Membership,
        on_delete=models.PROTECT,
        related_name="received_assignments",
    )

    attempt_number = models.PositiveIntegerField(default=1)
    offered_at = models.DateTimeField(default=timezone.now)

    response_cutoff_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    state = models.CharField(
        max_length=30,
        choices=AssignmentState.choices,
        default=AssignmentState.OFFERED,
    )

    responded_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    accepted_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    declined_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    decline_reason = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = [
            "-offered_at",
            "task_occurrence",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["task_occurrence", "attempt_number"],
                name="unique_assignment_attempt_per_occurrence",
            )
        ]

    def __str__(self):
        return (
            f"{self.task_occurrence.task.title} assigned to "
            f"{self.offered_to_membership.display_name}"
        )