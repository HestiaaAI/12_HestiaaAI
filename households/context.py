"""Request-scoped household selection; membership is revalidated on every call."""
from .models import Membership


class HouseholdRequired(Exception):
    pass


def active_memberships(user):
    rows = Membership.objects.select_related('workspace')
    return rows.filter(user=user, is_active=True) if user.is_authenticated else rows.none()


def resolve_active_membership(request):
    rows = active_memberships(request.user)
    selected = request.session.get('active_workspace_id')
    membership = next((m for m in rows if str(m.workspace_id) == str(selected)), None)
    if membership is None:
        request.session.pop('active_workspace_id', None)
        choices = list(rows)
        if len(choices) == 1:
            membership = choices[0]
    # Resolution does not persist an automatic choice on GET. Only switch POST
    # mutates selection; one-member households need no stored selection.
    request.active_membership = membership
    request.active_household = membership.workspace if membership else None
    request.household_memberships = rows
    return membership


def require_household(request):
    membership = resolve_active_membership(request)
    if membership is None:
        raise HouseholdRequired()
    return membership
