from django.views.generic import TemplateView
from django.shortcuts import redirect


class HomePageView(TemplateView):
    """Root page at / so the site does not 404 at the home URL."""

    template_name = "home.html"

    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if request.active_membership:
                return redirect('task_forms:board')
            return redirect('households:list' if request.household_memberships else 'households:onboarding')
        return super().get(request, *args, **kwargs)
