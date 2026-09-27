from django.views.generic import TemplateView


class HomePageView(TemplateView):
    """Root page at / so the site does not 404 at the home URL."""

    template_name = "home.html"
