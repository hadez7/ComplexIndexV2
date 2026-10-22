from django import template
import re
from django.utils.html import escape
from django.utils.safestring import mark_safe

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


@register.filter
def highlight_word(text, word):
    """
    Resalta apariciones de una palabra dentro de un texto usando <mark>.
    Insensible a mayúsculas/minúsculas y acentos pero preservando el texto original.
    """
    if not text or not word:
        return text or ""

    escaped_text = escape(str(text))
    word_clean = str(word).strip()
    if not word_clean:
        return mark_safe(escaped_text)

    vowel_map = {
        'a': '[aáAÁ]', 'á': '[aáAÁ]',
        'e': '[eéEÉ]', 'é': '[eéEÉ]',
        'i': '[iíIÍ]', 'í': '[iíIÍ]',
        'o': '[oóOÓ]', 'o': '[oóOÓ]',
        'u': '[uúüUÚÜ]', 'ú': '[uúüUÚÜ]', 'ü': '[uúüUÚÜ]',
    }
    pattern_parts = []
    for char in word_clean:
        char_lower = char.lower()
        if char_lower in vowel_map:
            pattern_parts.append(vowel_map[char_lower])
        else:
            pattern_parts.append(re.escape(escape(char)))

    regex_str = rf'(\b{"".join(pattern_parts)}\b)'
    pattern = re.compile(regex_str, re.IGNORECASE)
    highlighted = pattern.sub(r'<mark>\1</mark>', escaped_text)
    return mark_safe(highlighted)
