"""One resolved-route policy for household pages and private exports.

Allauth/admin retain their own policies. Views recheck actors inside mutation
transactions; the request snapshot is only a read-time optimization.
"""
from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils.cache import add_never_cache_headers, patch_vary_headers
from django.utils.deprecation import MiddlewareMixin

from .context import HouseholdRequired, resolve_active_membership


class HouseholdContextMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        match = request.resolver_match
        if match is None:
            return None
        name = match.view_name
        data = name == 'workflows:task-export-csv' or name in {'expenses:export', 'expenses:push-config', 'expenses:push-subscribe', 'expenses:push-unsubscribe'}
        household = match.app_name in {'workflows', 'task_forms', 'ai_tasks', 'groceries', 'expenses'} or name == 'product-lookup'
        private = household or match.app_name == 'households' or name == 'accounts:avatar'
        request._household_data = data
        request._private_response = private
        if private and not request.user.is_authenticated and name != 'households:accept-invite':
            if data:
                return JsonResponse({'error': 'Authentication required.'}, status=401)
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        # Invalid switch must not alter even a stale session; the POST handler
        # queries membership independently before changing selection.
        if name != 'households:switch':
            resolve_active_membership(request)
        if household and request.active_membership is None:
            return self.household_required_response(request)

    @staticmethod
    def household_required_response(request):
        if getattr(request, '_household_data', False):
            return JsonResponse({'error': 'Select a household to continue.', 'code': 'household_required'}, status=409)
        return redirect('households:list' if request.household_memberships else 'households:onboarding')

    def process_exception(self, request, exception):
        if isinstance(exception, HouseholdRequired):
            resolve_active_membership(request, refresh=True)
            return self.household_required_response(request)

    def process_response(self, request, response):
        match = getattr(request, 'resolver_match', None)
        if match and match.view_name == 'households:accept-invite':
            from .invitation_acceptance import private_invitation_response
            response = private_invitation_response(response)
        if getattr(request, '_private_response', False) or request.user.is_authenticated:
            add_never_cache_headers(response)
            patch_vary_headers(response, ('Cookie',))
        return response
