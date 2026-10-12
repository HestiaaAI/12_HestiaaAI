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
