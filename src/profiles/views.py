# src/profiles/views.py
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render

from profiles.models import Profile


@login_required
def student_profile_entry(request):
    if getattr(request.user, "role", None) != "student":
        return HttpResponseForbidden("Students only.")

    # Safe either way:
    # - If signal already created it, this is a no-op.
    # - If not (old users), this creates it on first visit.
    profile, _ = Profile.objects.get_or_create(user=request.user)

    context = {
        "active_nav": "profile",
        "profile": profile,
        "profile_complete": profile.is_complete(),  # currently False until we add fields
    }
    return render(request, "profiles/profile.html", context)
