from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from profiles.models import Profile
from profiles.utils import require_complete_profile


@login_required
def gate(request):
    """
    If the student’s profile is complete → send them to the real assessment home.
    Otherwise → show a holding page with a CTA back to Profile.
    """
    profile, _ = Profile.objects.get_or_create(user=request.user, defaults={"phone": ""})
    profile_complete = profile.is_complete()
    if profile_complete:
        return redirect("assessments:home")
    context = {
        "profile": profile,
        "profile_complete": profile_complete,
    }
    return render(request, "assessments/locked.html", context)


@login_required
@require_complete_profile
def home(request):
    # Your real assessments landing (placeholder)
    return render(request, "assessments/home.html", {})
