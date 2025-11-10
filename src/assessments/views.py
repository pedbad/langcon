from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

@login_required
def home(request):
    """
    Assessments landing page.
    If the student's profile is incomplete, show a warning card with a CTA to complete profile.
    """
    prof = getattr(request.user, "profile", None)
    profile_complete = bool(prof and prof.is_complete())

    if not profile_complete:
        # If your base template renders Django messages, this shows a warning toast.
        messages.warning(request, "Please complete your profile before starting your assessment.")

    return render(request, "assessments/home.html", {"profile_complete": profile_complete})
