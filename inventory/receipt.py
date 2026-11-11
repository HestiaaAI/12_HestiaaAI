"""Extract draft grocery rows from common English receipt layouts."""

import re

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


def receipt_drafts(text):
    rows = []
    for line in text.splitlines():
        line = " ".join(line.split())
        detail = QUANTITY_LINE.match(line)
        if detail:
            if rows and rows[-1]["quantity"] is None:
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
        count = COUNT_PREFIX.match(name)
        if count:
            name = name[count.end():]
        if not any(character.isalpha() for character in name) or SUMMARY.match(name):
            continue
        if len(rows) == MAX_RECEIPT_ROWS:
            break
        rows.append({
            "name": name[:100],
            "quantity": count.group(1) if count else None,
            "unit": "item",
        })
    return rows
