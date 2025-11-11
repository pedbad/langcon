# src/assessments/views.py

# Django imports
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render

# Local app imports
from profiles.models import Profile
from profiles.utils import require_complete_profile

from .llm_client import get_openai_client


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


@login_required
def llm_test(request):
    """
    Temporary dev/test view for checking OpenAI connectivity.
    Accessible only to logged-in users.
    """
    client = get_openai_client()
    model = "gpt-4o-mini"

    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Say 'Hello from LangCon'"}],
            max_tokens=6,
        )
        content = resp.choices[0].message.content
        return JsonResponse({"ok": True, "model": model, "reply": content})
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)})
