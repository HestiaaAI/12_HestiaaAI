from django.db.models import QuerySet

from .models import Task


def filter_task_queryset(queryset: QuerySet[Task], *, q: str = "", workspace_name: str = "") -> QuerySet[Task]:
    """Filter by title and related workspace name; blank terms are ignored.

    ``workspace__name__icontains`` spans the Task -> Workspace foreign key.
    Supplying both terms ANDs them. Results are ordered by primary key.
    """
    q = q.strip()
    workspace_name = workspace_name.strip()
    if q:
        queryset = queryset.filter(title__icontains=q)
    if workspace_name:
        queryset = queryset.filter(workspace__name__icontains=workspace_name)
    return queryset.select_related("workspace").order_by("task_id")
