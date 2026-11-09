"""Household catalogue comparison page."""
from django.shortcuts import render
from django.views.decorators.http import require_GET
from households.context import require_household
from .external import ExternalAPIError, compare_products


@require_GET
def product_compare_page(request):
    """Same comparison as the JSON API, rendered for a browser."""
    query = request.GET.get("q", "")
    if not query.strip():
        return render(
            request,
            "lookup/products.html",
            {"q": "", "result": None, "error": None},
        )
    try:
        result = compare_products(query, workspace=require_household(request).workspace)
    except ExternalAPIError as exc:
        return render(
            request,
            "lookup/products.html",
            {"q": query.strip(), "result": None, "error": exc.message},
            status=exc.status,
        )
    return render(
        request,
        "lookup/products.html",
        {"q": result["query"], "result": result, "error": None},
    )
