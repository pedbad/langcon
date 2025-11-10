# src/assessments/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from profiles.utils import require_complete_profile


@login_required
@require_complete_profile
def home(request):
    # Placeholder page (gated).
    # You can flesh this out later with your real assessment flow.
    return render(request, "assessments/home.html")
