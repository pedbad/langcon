# src/profiles/views.py
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden
from django.shortcuts import render

@login_required
def student_profile_entry(request):
    # Students only for now
    if getattr(request.user, "role", None) != "student":
        return HttpResponseForbidden("Students only.")
    return render(request, "profiles/coming_soon.html")
