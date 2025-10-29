# src/core/templatetags/form_extras.py
from django import template

register = template.Library()


@register.filter(name="add_attrs")
def add_attrs(field, attrs: str):
    """
    Usage: {{ field|add_attrs:'class:h-10 ...; placeholder:Email' }}
    Semicolon-separated key:value pairs. Existing attrs are preserved.
    """
    params = {}
    for chunk in attrs.split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        if ":" not in chunk:
            continue
        key, val = chunk.split(":", 1)
        params[key.strip()] = val.strip()
    return field.as_widget(attrs=params)
