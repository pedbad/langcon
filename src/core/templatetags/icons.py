# src/core/templatetags/icons.py
from uuid import uuid4

from django import template
from django.template.loader import get_template, TemplateDoesNotExist
from django.utils.safestring import mark_safe

register = template.Library()

# search order is simple for now; we can prepend app-specific folders later
ICON_SEARCH_ORDER = ("core/icons",)


@register.simple_tag
def icon(
    name: str,
    class_: str = "h-5 w-5",
    label: str | None = None,
    stroke_width: int | float = 2,
    fill: str | None = None,
):
    """
    Usage:
      {% icon 'menu' %}
      {% icon 'menu' class_='h-6 w-6' %}
      {% icon 'menu' label='Open main menu' %}
      {% icon 'menu' class_='h-5 w-5' label='Open' stroke_width=1.5 fill='none' %}

    Renders an SVG template from core/icons/<name>.html with provided variables.
    If no label is given, the icon is treated as decorative (aria-hidden).
    """
    template_obj = None
    for prefix in ICON_SEARCH_ORDER:
        tpl_name = f"{prefix}/{name}.html"
        try:
            template_obj = get_template(tpl_name)
            break
        except TemplateDoesNotExist:
            continue

    if not template_obj:
        # fail softly; empty span placeholder
        return mark_safe(f"<span class='{class_}' aria-hidden='true'></span>")

    context = {
        "class": class_,
        "label": label,
        "title_id": f"icon-{name}-{uuid4().hex[:6]}",
        "stroke_width": stroke_width,
        "fill": fill,
    }
    return mark_safe(template_obj.render(context))
