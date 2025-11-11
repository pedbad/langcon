# utils.py
from functools import wraps

from django.shortcuts import redirect

from .models import Profile


def require_complete_profile(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        try:
            profile = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            return redirect("profiles:profile")

        if not profile.is_complete():
            return redirect("profiles:profile")
        return view(request, *args, **kwargs)

    return wrapper
