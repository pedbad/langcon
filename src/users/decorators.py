# src/users/decorators.py
from collections.abc import Iterable
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

ROLE_HOME = {
    "student": "users:student_home",
    "teacher": "users:teacher_home",
    "admin": "users:admin_home",
}


def _normalize_roles(allowed_roles) -> set[str]:
    """
    Support @role_required("teacher") and @role_required(["teacher","admin"])
    """
    if isinstance(allowed_roles, list | tuple | set):
        return set(allowed_roles)
    return {allowed_roles}


def role_required(allowed_roles: Iterable[str] | str):
    """
    Restrict a function view to specific role(s).
    Usage:
        @role_required("teacher")
        @role_required(["admin", "teacher"])
    """
    allowed = _normalize_roles(allowed_roles)

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapper(request, *args, **kwargs):
            role = getattr(request.user, "role", None)

            # Allowed → proceed
            if role in allowed:
                return view_func(request, *args, **kwargs)

            # Not allowed → try to send them to THEIR home
            target = ROLE_HOME.get(role)

            # If we don't know their role, or no target, go to landing
            if not target:
                messages.error(request, "You do not have permission to view this page.")
                return redirect("core:landing")

            # Prevent redirect loops: if we're already on the target view, 403
            current_view = getattr(request.resolver_match, "view_name", None)
            if current_view == target:
                # Avoid adding the message repeatedly in a loop scenario
                raise PermissionDenied("You do not have permission to view this page.")

            messages.error(request, "You do not have permission to view this page.")
            return redirect(target)

        return wrapper

    return decorator
