def household_context(request):
    membership = getattr(request, 'active_membership', None)
    return {
        'active_household': getattr(request, 'active_household', None),
        'active_membership': membership,
        'household_memberships': getattr(request, 'household_memberships', ()),
        'can_manage_household': bool(membership and membership.role == 'OWNER'),
    }
