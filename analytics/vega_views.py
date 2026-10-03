"""Embedded Vega-Lite charts, portable specifications and saved chart outputs."""
import json

from django.conf import settings
from django.http import FileResponse, Http404, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.decorators.http import require_GET

CHARTS = {
    "chart1": ("task-priorities", "api:chart-priorities"),
    "chart2": ("task-creations", "api:chart-creations"),
}
ARTIFACTS = settings.BASE_DIR / "docs" / "a4-person-1"


@require_GET
def charts(request):
    return render(request, "analytics/vega_charts.html")


@require_GET
def chart_spec(request, chart):
    if chart not in CHARTS:
        raise Http404("Unknown chart")
    filename, api_route = CHARTS[chart]
    spec = json.loads((ARTIFACTS / "specs" / f"{filename}.vl.json").read_text(encoding="utf-8"))
    # An absolute URL lets the same downloaded spec work in the online editor.
    spec["data"]["url"] = request.build_absolute_uri(reverse(api_route))
    response = JsonResponse(spec, json_dumps_params={"indent": 2})
    response["Access-Control-Allow-Origin"] = "*"
    return response


@require_GET
def chart_image(request, chart):
    if chart not in CHARTS:
        raise Http404("Unknown chart")
    filename, _ = CHARTS[chart]
    path = ARTIFACTS / "outputs" / f"{filename}.png"
    if not path.is_file():
        raise Http404("Chart snapshot has not been generated")
    return FileResponse(path.open("rb"), content_type="image/png")
