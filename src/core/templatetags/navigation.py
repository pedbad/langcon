# src/core/templatetags/navigation.py
from django import template
from django.urls import resolve, Resolver404
from django.utils.safestring import mark_safe

register = template.Library()


def _is_active_by_view(request, view_name: str) -> bool:
    """Return True if the current resolved view name equals view_name."""
    try:
        current = resolve(request.path_info)
        return current.view_name == view_name
    except Resolver404:
        return False


def _is_active(request, view_names: tuple[str, ...], startswith: str | None) -> bool:
    """Shared matcher for both tags."""
    if not request:
        return False
    # view-name match
    for name in view_names:
        if _is_active_by_view(request, name):
            return True
    # path prefix match
    if startswith and request.path.startswith(startswith):
        return True
    return False


@register.simple_tag(takes_context=True)
def active_url(
    context,
    *view_names,
    startswith: str | None = None,
    active_class: str = "is-active",
):
    """
    Usage in templates:
      class="nav-link {% active_url 'core:landing' %}"
      class="nav-link {% active_url 'core:about' startswith='/about/' %}"

    Returns a neutral hook (default: "is-active") when active; else empty string.
    Avoids styling (color) here so CSS controls the look.
    """
    request = context.get("request")
    return active_class if _is_active(request, view_names, startswith) else ""


@register.simple_tag(takes_context=True)
def aria_current(context, *view_names, startswith: str | None = None):
    """
    Usage in templates:
      {% aria_current 'core:landing' %}
      {% aria_current 'core:about' startswith='/about/' %}

    Returns aria-current="page" (marked safe) when active; else empty string.
    """
    request = context.get("request")
    if _is_active(request, view_names, startswith):
        # mark safe so quotes are not escaped in templates,
        # works inline or via "as var"
        return mark_safe('aria-current="page"')
    return ""
