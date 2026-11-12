from decimal import Decimal
from django import template
from django.utils.safestring import mark_safe
register = template.Library()


@register.filter
def usd(value):
    return f"${Decimal(value or 0) / 100:,.2f}"


@register.filter
def initials(value):
    words = str(value).split()
    return "".join(word[0] for word in words[:2]).upper() or "?"


@register.simple_tag
def icon(name):
    paths = {
        "tasks": '<rect x="4" y="4" width="16" height="16" rx="3"/><path d="m8 12 3 3 6-7"/>',
        "wallet": '<path d="M3 6h16v14H3zM3 6l14-3v3m-2 6h6v4h-6z"/>',
        "people": '<circle cx="9" cy="7" r="3"/><path d="M2 20v-3a7 7 0 0 1 14 0v3m0-16a3 3 0 0 1 0 6m3 3c2 1 3 3 3 6"/>',
        "groceries": '<path d="M5 7h14l-1 14H6zM9 9V6a3 3 0 0 1 6 0v3"/>',
        "arrow": '<path d="m9 5 7 7-7 7"/>',
        "back": '<path d="m15 5-7 7 7 7"/>',
        "plus": '<path d="M12 5v14M5 12h14"/>',
        "leaf": '<path d="M5 19C-2 3 16 2 21 3c1 14-9 17-16 16Zm0 0L16 7"/>',
        "check": '<path d="m5 12 4 4L19 6"/>',
        "search": '<circle cx="10" cy="10" r="6"/><path d="m15 15 6 6"/>',
        "receipt": '<path d="M5 3h14v18l-3-2-4 2-4-2-3 2zm3 5h8m-8 4h6"/>',
        "home": '<path d="m3 10 9-7 9 7M5 9v12h14V9M10 21v-7h4v7"/>',
        "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v6l4 2"/>',
    }
    return mark_safe('<svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">' + paths.get(name, paths["receipt"]) + '</svg>')


@register.filter
def dollars(value):
    return f"{Decimal(value or 0) / 100:.2f}"

@register.filter
def money(value):
    return f'{Decimal(value or 0)/100:.2f}'
