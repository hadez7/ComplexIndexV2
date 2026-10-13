from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)


@register.filter
def compact_number(val):
    try:
        val = float(val)
        if val >= 1_000_000:
            return f"{val / 1_000_000:.1f}M"
        elif val >= 1_000:
            return f"{val / 1_000:.1f}k"
        return f"{int(val)}"
    except (ValueError, TypeError):
        return val


@register.filter
def intcomma(val):
    try:
        val = int(val)
        return f"{val:,}"
    except (ValueError, TypeError):
        return val