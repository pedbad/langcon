# utils.py
from functools import wraps

from django.shortcuts import redirect


def require_complete_profile(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        profile = getattr(request.user, "profile", None)
        if not profile or not profile.is_complete():
            return redirect("profiles:profile")
        return view(request, *args, **kwargs)

    return wrapper
