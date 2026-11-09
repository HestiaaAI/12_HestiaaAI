"""A5 route access policy shared by HTML views and JSON APIs."""
from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.utils.deprecation import MiddlewareMixin


class AssignmentAccessMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        match = request.resolver_match
        if request.user.is_authenticated or match is None:
            return None
        if match.app_name in {"workflows", "task_forms", "task_search", "reports", "analytics"} or match.view_name == "product-lookup":
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        return None


class HouseholdContextMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        from django.shortcuts import redirect
        from django.http import JsonResponse
        match = request.resolver_match
        if match is None:
            return None
        name = match.view_name
        # A rejected switch must preserve the session byte-for-byte, even if
        # its previous selection is stale. The POST view validates independently.
        if name == 'households:switch':
            return None
        from .context import resolve_active_membership
        resolve_active_membership(request)
        stateless = name == 'ask-hestia'
        household = not stateless and (match.app_name in {'workflows', 'task_forms', 'ai_tasks', 'analytics'} or name == 'product-lookup')
        request._household_response = household
        data = name in {'workflows:task-export-csv', 'analytics:task-priority-chart'}
        request._household_data = data
        if household and not request.user.is_authenticated:
            if data:
                return JsonResponse({'error': 'Authentication required.'}, status=401)
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        if household and request.active_membership is None:
            if data:
                return JsonResponse({'error': 'Select a household to continue.', 'code': 'household_required'}, status=409)
            return redirect('households:list' if request.household_memberships.exists() else 'households:onboarding')

    def process_response(self, request, response):
        if getattr(request, '_household_response', False) or request.user.is_authenticated:
            from django.utils.cache import add_never_cache_headers, patch_vary_headers
            add_never_cache_headers(response)
            patch_vary_headers(response, ('Cookie',))
        return response

    def process_exception(self, request, exception):
        from .context import HouseholdRequired
        if not isinstance(exception, HouseholdRequired):
            return None
        from django.http import JsonResponse
        from django.shortcuts import redirect
        if getattr(request, '_household_data', False):
            return JsonResponse({'error': 'Select a household to continue.', 'code': 'household_required'}, status=409)
        return redirect('households:list' if request.household_memberships.exists() else 'households:onboarding')
