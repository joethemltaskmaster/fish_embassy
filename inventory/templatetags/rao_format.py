"""Display filters — currency, quantity, dates. Never do math here."""

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()

_EM_DASH = "—"


@register.filter
def naira(value):
    """Format a Decimal/number as Nigerian naira: '₦21,000.00'."""
    if value is None or value == "":
        return _EM_DASH
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return _EM_DASH
    return f"₦{d:,.2f}"


@register.filter
def qty(value):
    """Format quantities: whole numbers without decimals, else 3 places."""
    if value is None or value == "":
        return _EM_DASH
    try:
        d = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return _EM_DASH
    if d == d.to_integral_value():
        return f"{int(d):,}"
    return f"{d:,.3f}"


@register.filter
def date_short(value):
    """Format a date as '31 Dec 2026'."""
    if not value:
        return _EM_DASH
    return value.strftime("%d %b %Y")


@register.filter
def datetime_short(value):
    """Format a datetime as '31 Dec 2026 · 14:35'."""
    if not value:
        return _EM_DASH
    return value.strftime("%d %b %Y · %H:%M")