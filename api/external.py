"""Compare a shopper's query with Open Food Facts and Hestia records.

Week 4's lecture calls a keyless API with requests.get(params=..., timeout=5),
raise_for_status(), and a polished subset of the JSON. This module follows that
pattern with Open Food Facts (the assignment excludes Open-Meteo) and joins the
result to household products, shopping-list rows, and shopping tasks. External
rows are never saved.
"""

import requests
from django.db.models import Q

from inventory.models import Product, ShoppingListEntry
from workflows.models import Task

OPEN_FOOD_FACTS_SEARCH_URL = "https://search.openfoodfacts.org/search"
SOURCE_NAME = "Open Food Facts"
REQUEST_TIMEOUT_SECONDS = 5
MAX_QUERY_LENGTH = 80
EXTERNAL_PAGE_SIZE = 5
USER_AGENT = "HestiaAI-INFO490/1.0 (educational class project)"


class ExternalAPIError(Exception):
    """A query or upstream failure the views can turn into a JSON error."""

    def __init__(self, message, status):
        super().__init__(message)
        self.message = message
        self.status = status


def compare_products(raw_query):
    """Return a processed comparison for one search term.

    Raises ExternalAPIError for a blank query or an upstream failure.
    """
    query = (raw_query or "").strip()
    if not query:
        raise ExternalAPIError("Provide a search term with ?q=.", 400)
    if len(query) > MAX_QUERY_LENGTH:
        raise ExternalAPIError("Search terms must be 80 characters or fewer.", 400)

    internal = _internal_matches(query)
    external = _fetch_open_food_facts(query)
    return _build_payload(query, internal, external)


def _internal_matches(query):
    """Read matching household rows. Nothing from the public API is written."""
    products = [
        {
            "id": product.product_id,
            "name": product.canonical_name,
            "workspace": product.workspace.name,
        }
        for product in Product.objects.filter(canonical_name__icontains=query)
        .select_related("workspace")
        .order_by("product_id")
    ]
    shopping_items = [
        {
            "id": entry.shopping_list_entry_id,
            "name": entry.item_name,
            "state": entry.state,
            "workspace": entry.workspace.name,
        }
        for entry in ShoppingListEntry.objects.filter(item_name__icontains=query)
        .select_related("workspace")
        .order_by("shopping_list_entry_id")
    ]
    shopping_tasks = [
        {
            "id": task.task_id,
            "title": task.title,
            "workspace": task.workspace.name,
        }
        for task in Task.objects.filter(
            Q(task_type=Task.TaskType.SHOPPING) & Q(title__icontains=query)
        )
        .select_related("workspace")
        .order_by("task_id")
    ]
    return {
        "products": products,
        "shopping_items": shopping_items,
        "shopping_tasks": shopping_tasks,
    }


def _fetch_open_food_facts(query):
    """GET a short product list. The lecture's three calls are required here."""
    params = {
        "q": query,
        "page_size": EXTERNAL_PAGE_SIZE,
        "fields": "code,product_name,brands,nutrition_grades,quantity",
    }
    try:
        response = requests.get(
            OPEN_FOOD_FACTS_SEARCH_URL,
            params=params,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.exceptions.RequestException as exc:
        raise ExternalAPIError(
            "Open Food Facts could not be reached. Try again in a moment.",
            502,
        ) from exc

    if not isinstance(payload, dict):
        raise ExternalAPIError("Open Food Facts returned an unexpected response.", 502)

    hits = payload.get("hits", [])
    if not isinstance(hits, list):
        hits = []

    products = []
    for hit in hits[:EXTERNAL_PAGE_SIZE]:
        if not isinstance(hit, dict):
            continue
        name = str(hit.get("product_name") or "").strip()
        if not name:
            continue
        grade = str(hit.get("nutrition_grades") or "").strip().lower() or "unknown"
        products.append(
            {
                "code": str(hit.get("code") or ""),
                "name": name,
                "brands": _brand_label(hit.get("brands")),
                "nutriscore": grade,
                "quantity": str(hit.get("quantity") or "").strip(),
            }
        )

    match_count = payload.get("count")
    if not isinstance(match_count, int):
        match_count = len(products)
    return {
        "products": products,
        "match_count": match_count,
        "match_count_exact": bool(payload.get("is_count_exact")),
    }


def _brand_label(brands):
    if isinstance(brands, list):
        names = [str(brand).strip() for brand in brands if str(brand).strip()]
        return ", ".join(names)
    return str(brands or "").strip()


def _names_overlap(left, right):
    first = left.casefold().strip()
    second = right.casefold().strip()
    if len(first) < 3 or len(second) < 3:
        return False
    return first in second or second in first


def _build_payload(query, internal, external):
    household_names = [row["name"] for row in internal["products"]]
    household_names.extend(row["name"] for row in internal["shopping_items"])

    already_listed = []
    new_to_household = []
    for product in external["products"]:
        listed = any(_names_overlap(product["name"], name) for name in household_names)
        (already_listed if listed else new_to_household).append(product["name"])

    grade_counts = {}
    for product in external["products"]:
        grade = product["nutriscore"]
        grade_counts[grade] = grade_counts.get(grade, 0) + 1
    nutriscore_counts = [
        {"grade": grade, "count": grade_counts[grade]}
        for grade in sorted(grade_counts)
    ]

    product_count = len(internal["products"])
    item_count = len(internal["shopping_items"])
    task_count = len(internal["shopping_tasks"])
    shown = len(external["products"])
    if external["match_count_exact"]:
        reported = f"{external['match_count']} public match(es)"
    else:
        reported = f"at least {external['match_count']} public matches"
    summary = (
        f'{product_count} household product(s), {item_count} shopping-list item(s), '
        f'and {task_count} shopping task(s) match "{query}". '
        f"Open Food Facts returned {shown} product(s) to compare ({reported}). "
        f"{len(already_listed)} of those already appear in this household; "
        f"{len(new_to_household)} do not."
    )

    return {
        "ok": True,
        "query": query,
        "source": {"name": SOURCE_NAME, "url": "https://world.openfoodfacts.org/"},
        "internal": internal,
        "external": {
            "products": external["products"],
            "match_count": external["match_count"],
            "match_count_exact": external["match_count_exact"],
        },
        "analysis": {
            "internal_product_count": product_count,
            "internal_shopping_item_count": item_count,
            "internal_shopping_task_count": task_count,
            "external_shown": shown,
            "nutriscore_counts": nutriscore_counts,
            "already_in_household": already_listed,
            "new_to_household": new_to_household,
            "summary": summary,
        },
    }
