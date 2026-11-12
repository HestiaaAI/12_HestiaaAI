"""Request-scoped household selection; membership is loaded once per normal request."""
from .models import Membership


class HouseholdRequired(Exception):
    pass


def active_memberships(user):
    rows = Membership.objects.select_related('workspace', 'user__hestia_avatar')
    return rows.filter(user=user, is_active=True) if user.is_authenticated else rows.none()


def resolve_active_membership(request, *, refresh=False):
    if not refresh and getattr(request, "_household_context_resolved", False):
        return request.active_membership
    rows = tuple(active_memberships(request.user))
    selected = request.session.get('active_workspace_id')
    membership = next((m for m in rows if str(m.workspace_id) == str(selected)), None)
    if membership is None:
        request.session.pop('active_workspace_id', None)
        if len(rows) == 1:
            membership = rows[0]
    # Resolution does not persist an automatic choice on GET. Only switch POST
    # mutates selection; one-member households need no stored selection.
    request._household_context_resolved = True
    request.active_membership = membership
    request.active_household = membership.workspace if membership else None
    request.household_memberships = rows
    return membership


def require_household(request):
    membership = resolve_active_membership(request)
    if membership is None:
        raise HouseholdRequired()
    return membership


def fresh_household(request):
    """Fresh access check immediately before an external provider invocation."""
    selected = require_household(request)
    try:
        return Membership.objects.select_related('workspace', 'user__hestia_avatar').get(
            pk=selected.pk, user=request.user, workspace_id=selected.workspace_id,
            is_active=True, user__is_active=True)
    except Membership.DoesNotExist:
        raise HouseholdRequired()
