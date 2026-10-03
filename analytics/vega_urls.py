from django.urls import path

from . import vega_views

app_name = "vega"

urlpatterns = [
    path("", vega_views.charts, name="charts"),
    path("<str:chart>.json", vega_views.chart_spec, name="spec"),
    path("<str:chart>.png", vega_views.chart_image, name="image"),
]
