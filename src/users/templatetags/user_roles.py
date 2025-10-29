from django import template

register = template.Library()


# --- role checks as filters ---------------------------------------------------
@register.filter
def is_admin(user):
    """
    Usage: {% if request.user|is_admin %} ... {% endif %}
    Allows superusers OR role == 'admin'.
    """
    if not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False):
        return True
    return getattr(user, "role", None) == "admin"


@register.filter
def is_teacher(user):
    """
    Usage: {% if request.user|is_teacher %} ... {% endif %}
    """
    if not getattr(user, "is_authenticated", False):
        return False
    return getattr(user, "role", None) == "teacher"


@register.filter
def is_student(user):
    """
    Usage: {% if request.user|is_student %} ... {% endif %}
    """
    if not getattr(user, "is_authenticated", False):
        return False
    return getattr(user, "role", None) == "student"


# --- additional: assignment-style tags (nice for reuse in larger templates) ----
# --- Tags let you compute once at the top of a big template and reuse the boolean multiple times.
@register.simple_tag(takes_context=True)
def user_is_admin(context):
    """
    Usage:
      {% user_is_admin as admin_user %}
      {% if admin_user %} ... {% endif %}
    """
    user = context.get("request").user
    return is_admin(user)  # reuse the filter logic


@register.simple_tag(takes_context=True)
def user_is_teacher(context):
    user = context.get("request").user
    return is_teacher(user)


@register.simple_tag(takes_context=True)
def user_is_student(context):
    user = context.get("request").user
    return is_student(user)
