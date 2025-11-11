# src/profiles/views.py
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import redirect, render

from .forms import ProfileForm
from .models import Profile

logger = logging.getLogger(__name__)


@login_required
def student_profile_entry(request):
    if getattr(request.user, "role", None) != "student":
        return HttpResponseForbidden("Students only.")

    profile, _ = Profile.objects.get_or_create(
        user=request.user,
        defaults={"phone": ""},
    )

    profile_readonly = profile.is_locked or profile.is_complete()

    if request.method == "POST":
        if profile_readonly:
            return HttpResponseForbidden("Profile is locked.")

        post_snapshot = {k: request.POST.getlist(k) for k in request.POST}
        logger.info("Profile POST payload for %s: %s", request.user, post_snapshot)

        form = ProfileForm(request.POST, instance=profile)
        if form.is_valid():
            saved_profile = form.save()
            logger.info(
                (
                    "Profile saved for %s — has_exam=%s exam_type=%s exam_date=%s "
                    "reading=%s overall=%s cam_grade=%s"
                ),
                request.user,
                saved_profile.has_recent_english_exam,
                saved_profile.exam_type,
                saved_profile.exam_date,
                saved_profile.reading_score,
                saved_profile.overall_score,
                saved_profile.cambridge_grade,
            )
            messages.success(request, "Your profile has been saved.")
            return redirect("profiles:profile")  # PRG pattern
        else:
            logger.warning("Profile form errors for %s: %s", request.user, form.errors)
    else:
        form = ProfileForm(instance=profile)

    context = {
        "active_nav": "profile",
        "profile": profile,
        "profile_complete": profile.is_complete(),
        "form": form,
        "form_readonly": profile_readonly,
    }
    return render(request, "profiles/profile.html", context)
