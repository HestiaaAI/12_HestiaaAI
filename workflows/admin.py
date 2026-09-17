from django.contrib import admin

from .models import Assignment, Task, TaskOccurrence


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        "task_id",
        "title",
        "task_type",
        "priority",
        "workspace",
        "created_by_membership",
    )
    search_fields = (
        "title",
        "description",
        "workspace__name",
        "created_by_membership__display_name",
        "related_product__canonical_name",
    )
    list_filter = (
        "task_type",
        "priority",
        "workspace",
    )
    ordering = ("-created_at",)
    list_select_related = (
        "workspace",
        "created_by_membership",
        "source_document",
        "related_product",
        "related_shopping_list_entry",
    )


@admin.register(TaskOccurrence)
class TaskOccurrenceAdmin(admin.ModelAdmin):
    list_display = (
        "task_occurrence_id",
        "task",
        "sequence",
        "scheduled_for",
        "due_at",
        "state",
    )
    search_fields = ("task__title",)
    list_filter = (
        "state",
        "task__task_type",
    )
    ordering = ("due_at",)
    list_select_related = ("task",)
    date_hierarchy = "due_at"


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "assignment_id",
        "task_occurrence",
        "offered_to_membership",
        "proposed_by_membership",
        "attempt_number",
        "state",
        "offered_at",
        "responded_at",
    )
    search_fields = (
        "task_occurrence__task__title",
        "offered_to_membership__display_name",
        "proposed_by_membership__display_name",
    )
    list_filter = (
        "state",
        "offered_to_membership__role",
    )
    ordering = ("-offered_at",)
    list_select_related = (
        "task_occurrence",
        "task_occurrence__task",
        "offered_to_membership",
        "proposed_by_membership",
    )