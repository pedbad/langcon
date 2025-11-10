# src/profiles/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from .forms import ProfileForm
from .models import Profile


@login_required
def student_profile_entry(request):
    if getattr(request.user, "role", None) != "student":
        return HttpResponseForbidden("Students only.")

    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={"phone": ""},
    )

    if request.method == "POST":
        if profile.is_locked:
            return HttpResponseForbidden("Profile is locked.")

        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been saved.")
            return redirect("profiles:profile")  # PRG pattern
    else:
        form = ProfileForm(instance=profile)

    context = {
        "active_nav": "profile",
        "profile": profile,
        "profile_complete": profile.is_complete(),
        "form": form,
    }
    return render(request, "profiles/profile.html", context)
