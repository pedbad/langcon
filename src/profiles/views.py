# src/profiles/views.py
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from profiles.models import Profile

from .forms import ProfileForm


@login_required
def student_profile_entry(request):
    if getattr(request.user, "role", None) != "student":
        return HttpResponseForbidden("Students only.")

    # Safe either way:
    # - If signal already created it, this is a no-op.
    # - If not (old users), this creates it on first visit.
    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={"phone": ""},  # <-- keep this to allow first-time creation
    )

    if request.method == "POST":
        # Prevent editing if locked
        if profile.is_locked:
            return HttpResponseForbidden("Profile is locked.")
        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            return redirect("profiles:profile")
    else:
        form = ProfileForm(instance=profile)

    context = {
        "active_nav": "profile",
        "profile": profile,
        "profile_complete": profile.is_complete(),
        "form": form,
    }
    return render(request, "profiles/profile.html", context)
