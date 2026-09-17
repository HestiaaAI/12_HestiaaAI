from django.contrib import admin

from .models import Membership, Workspace


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = (
        "workspace_id",
        "name",
        "workspace_type",
        "timezone",
        "created_at",
    )
    search_fields = (
        "name",
        "timezone",
    )
    list_filter = (
        "workspace_type",
    )
    ordering = (
        "name",
    )


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = (
        "membership_id",
        "display_name",
        "workspace",
        "user",
        "role",
        "is_active",
    )
    search_fields = (
        "display_name",
        "workspace__name",
        "user__username",
        "user__email",
    )
    list_filter = (
        "role",
        "is_active",
        "workspace",
    )
    ordering = (
        "workspace",
        "display_name",
    )
    list_select_related = (
        "workspace",
        "user",
    )