"""A5: one public data API; all other API routes require a Django session."""
from django.contrib.auth.views import redirect_to_login
from django.http import JsonResponse
from django.utils.cache import add_never_cache_headers, patch_vary_headers
from django.utils.deprecation import MiddlewareMixin


class ApiAccessMiddleware(MiddlewareMixin):
    def process_view(self, request, view_func, view_args, view_kwargs):
        match = request.resolver_match
        # Match resolved routes, not URL substrings or user-supplied parameters.
        private_api = "api" in match.namespaces and match.view_name != "api:chart-priorities"
        private_export = match.view_name in {"reports:tasks-json", "reports:tasks-csv"}
        private_chart = "vega" in match.namespaces and view_kwargs.get("chart") == "chart2"
        private_page = match.view_name in {"reports:task-report", "product-lookup"}
        request._private_data_response = private_api or private_export or private_chart or private_page
        if request._private_data_response and not request.user.is_authenticated:
            if private_page:
                return redirect_to_login(request.get_full_path())
            return JsonResponse({"error": "Authentication required."}, status=401)

    def process_response(self, request, response):
        if getattr(request, "_private_data_response", False):
            add_never_cache_headers(response)
            patch_vary_headers(response, ("Cookie",))
        return response
