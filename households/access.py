"""A5 route access policy shared by HTML views and JSON APIs."""
from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.utils.deprecation import MiddlewareMixin


class AssignmentAccessMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        match = request.resolver_match
        if request.user.is_authenticated or match is None:
            return None
        if match.view_name in settings.PUBLIC_API_VIEW_NAMES:
            return None
        if match.app_name in {"workflows", "task_forms", "task_search", "reports", "analytics"} or match.view_name == "product-lookup":
            return redirect_to_login(request.get_full_path(), settings.LOGIN_URL)
        return None


class HouseholdContextMiddleware(MiddlewareMixin):
    def process_request(self, request):
        from .context import resolve_active_membership
        resolve_active_membership(request)

    def process_view(self, request, view_func, view_args, view_kwargs):
        from django.shortcuts import redirect
        from django.http import JsonResponse
        match = request.resolver_match
        if match is None:
            return None
        name = match.view_name
        public = name == 'api:chart-priorities' or (match.app_name == 'vega' and view_kwargs.get('chart') == 'chart1')
        stateless = name in {'ask-hestia', 'api:brain-dump', 'api:response-demo'}
        household = not public and not stateless and (match.app_name in {'workflows', 'task_forms', 'task_search', 'reports', 'analytics', 'vega', 'api'} or name == 'product-lookup')
        request._household_response = household
        data = match.app_name == 'api' or name in {'reports:tasks-json', 'reports:tasks-csv', 'analytics:task-priority-chart', 'vega:spec', 'vega:image'}
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
