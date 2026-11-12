"""Extract draft grocery rows from common English receipt layouts."""

import re
from datetime import datetime, timedelta
from django.utils import timezone

MAX_RECEIPT_ROWS = 40
MAX_RECEIPT_TEXT = 16000
PRICE = re.compile(r"\s+\$?\d+[.,]\d{2}(?:\s+[A-Z]{1,2})?\s*$", re.I)
SUMMARY = re.compile(
    r"^(?:sub[\s-]*total|total|tax|sales tax|balance|amount|cash|change|"
    r"visa|mastercard|debit|credit|card|payment|tender|coupon|discount|"
    r"savings|loyalty|member|receipt|transaction|register|cashier|"
    r"approved|authorization|refund|rounding|thank you)\b", re.I,
)
QUANTITY_LINE = re.compile(
    r"^(\d{1,7}(?:\.\d{1,3})?)\s*(lb|lbs|kg|oz|g|x|@)\s*(?:@|x|\$|\d|$)",
    re.I,
)
COUNT_PREFIX = re.compile(r"^(\d{1,7})\s*[x×]\s+", re.I)


def receipt_purchase_date(text, fallback=None):
    for match in re.finditer(r"(?:date|purchased)\s*:?\s*(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4})", text, re.I):
        for fmt in ("%Y-%m-%d", "%m/%d/%Y"):
            try:
                return datetime.strptime(match.group(1), fmt).date()
            except ValueError:
                pass
    return fallback or timezone.localdate()


def stock_suggestion(name, purchased_on):
    # Editable demo estimates for newly bought, unopened goods, not package dates.
    rules = [
        (r"frozen|ice cream|ice cubes", "freezer", 90),
        (r"soap|detergent|skincare", "pantry", None),
        (r"chicken|fish|salmon|beef|turkey|deli", "fridge", None),
        (r"milk|paneer|yogurt|yoghurt|cheese|tofu|butter|cream", "fridge", 7),
        (r"bread", "pantry", 7),
        (r"egg", "fridge", 21),
        (r"banana|apple|orange|carrot|pepper|spinach", "fridge", 7),
        (r"rice|pasta|tea|coffee|lentil|chickpea|oats|sugar|salt|chocolate|cereal|flour|oil|cracker|biscuit|protein bars|breakfast supplies|sparkling water", "pantry", 180),
    ]
    for pattern, storage, days in rules:
        if re.search(r"\b(?:" + pattern + r")(?:s)?\b", name, re.I):
            return {"storage": storage, "expires_on": purchased_on + timedelta(days=days) if days is not None else None}
    return {"storage": "", "expires_on": None}


def receipt_drafts(text, purchased_on=None):
    purchased_on = purchased_on or receipt_purchase_date(text)
    rows = []
    for line in text.splitlines():
        line = " ".join(line.split())
        detail = QUANTITY_LINE.match(line)
        if detail:
            if rows:
                quantity, unit = detail.groups()
                unit = unit.lower()
                rows[-1].update(
                    quantity=quantity,
                    unit={"x": "item", "@": "item", "lbs": "lb"}.get(unit, unit),
                )
            continue

        price = PRICE.search(line)
        if not price:
            continue
        name = re.sub(r"^\d{4,15}\s+", "", line[:price.start()]).strip(" -:.*")
        inline = re.search(r"\s+(\d{1,4})\s*[x×@](?:\s*\$?\d+[.,]\d{2})?\s*$", name, re.I)
        inline_quantity = inline.group(1) if inline else None
        if inline:
            name = name[:inline.start()].strip()
        count = COUNT_PREFIX.match(name)
        if count:
            name = name[count.end():]
        if not any(character.isalpha() for character in name) or SUMMARY.match(name):
            continue
        if len(rows) == MAX_RECEIPT_ROWS:
            break
        rows.append({
            "name": name[:100],
            "quantity": count.group(1) if count else inline_quantity or "1",
            "unit": "item",
            **stock_suggestion(name, purchased_on),
        })
    return rows
