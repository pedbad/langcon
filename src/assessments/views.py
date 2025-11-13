# src/assessments/views.py

# Django imports
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

# Local app imports
from profiles.models import Profile
from profiles.utils import require_complete_profile

from .forms import WritingAnswerForm
from .llm_client import get_openai_client
from .models import Assessment

# add at the top with other imports
from .services.questions import generate_followups_from_statement


# ─────────────────────────────────────────────────────────────────────
# Helper: simple, robust word counter (server-side source of truth)
# ─────────────────────────────────────────────────────────────────────
def _count_words(text: str) -> int:
    text = (text or "").strip()
    return len([w for w in text.split() if w])


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
    context = {"profile": profile, "profile_complete": profile_complete}
    return render(request, "assessments/locked.html", context)


@login_required
@require_complete_profile
def home(request):
    """
    Assessment main view:
    - Shows the writing prompt and answer form.
    - Allows students to save drafts (even empty).
    - Enforces submit rules (250–300 words), locks final answer on submit.
    - After a successful submit, calls the LLM to generate two follow-up questions
      and stores them on the Assessment (llm_question_1/2).
    """

    assessment, _ = Assessment.objects.get_or_create(user=request.user)

    if request.method == "POST":
        action = request.POST.get("action")

        # Bind form once for both actions
        form = WritingAnswerForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Please check your input and try again.")
            return render(
                request, "assessments/home.html", {"assessment": assessment, "form": form}
            )

        answer = form.cleaned_data.get("writing_answer") or ""

        # Soft-cap safety for drafts (matches client maxlength)
        MAX_CHARS = 3000  # ≈ 500 words (client has maxlength="3000")
        if action == "save":
            if len(answer) > MAX_CHARS:
                # Truncate on server to avoid huge payloads; warn user (no silent data loss).
                assessment.writing_answer_draft = answer[:MAX_CHARS]
                assessment.save(update_fields=["writing_answer_draft", "updated_at"])
                messages.warning(
                    request,
                    (
                        f"Draft truncated to {MAX_CHARS} characters (≈500 words). "
                        "Please shorten your answer."
                    ),
                )

            else:
                assessment.writing_answer_draft = answer
                assessment.save(update_fields=["writing_answer_draft", "updated_at"])
                messages.success(request, "Draft saved.")
            return redirect("assessments:home")  # PRG

        # Submit path: enforce policy and lock
        if action == "submit":
            # Idempotency: if already submitted, do nothing further
            if assessment.writing_answer_final:
                messages.info(request, "Your writing answer is already submitted.")
                return redirect("assessments:home")

            # Authoritative server-side word count
            n_words = _count_words(answer)
            MIN_W, MAX_W = 250, 300

            if n_words < MIN_W or n_words > MAX_W:
                # Keep draft (truncated to MAX_CHARS if needed); do not lock
                assessment.writing_answer_draft = answer[:MAX_CHARS]
                assessment.save(update_fields=["writing_answer_draft", "updated_at"])
                messages.error(
                    request,
                    (
                        f"Your answer is {n_words} words. It must be between {MIN_W} and "
                        f"{MAX_W} words to submit."
                    ),
                )

                return render(
                    request,
                    "assessments/home.html",
                    {
                        "assessment": assessment,
                        "form": WritingAnswerForm(
                            initial={"writing_answer": assessment.writing_answer_draft}
                        ),
                    },
                )

            # ✅ Lock: copy draft → final and timestamp (no more edits after this)
            assessment.writing_answer_draft = answer[:MAX_CHARS]
            assessment.writing_answer_final = assessment.writing_answer_draft
            assessment.writing_submitted_at = timezone.now()
            assessment.save(
                update_fields=[
                    "writing_answer_draft",
                    "writing_answer_final",
                    "writing_submitted_at",
                    "updated_at",
                ]
            )

            # 🪝 LLM follow-up generation (sync, minimal)
            # Payload is just the *final* statement text; no subject area needed here.
            try:
                data = generate_followups_from_statement(assessment.writing_answer_final)
                q1 = (data.get("question1") or "").strip()
                q2 = (data.get("question2") or "").strip()
                if not q1 or not q2:
                    raise ValueError("Missing question1/question2 in LLM response")

                assessment.llm_question_1 = q1
                assessment.llm_question_2 = q2
                assessment.save(update_fields=["llm_question_1", "llm_question_2", "updated_at"])

                messages.success(request, "Submitted. Your first follow-up question is ready.")
            except Exception:
                # Keep the submission locked; allow retrying generation later.
                messages.warning(
                    request,
                    "Submitted. We’re preparing your follow-up questions, but there was a hiccup. "
                    "Please refresh shortly or try again later.",
                )

            return redirect("assessments:home")

        # Unknown action
        messages.error(request, "Unknown action.")
        return render(request, "assessments/home.html", {"assessment": assessment, "form": form})

    # GET: prefill form with current draft
    form = WritingAnswerForm(initial={"writing_answer": assessment.writing_answer_draft})
    return render(request, "assessments/home.html", {"assessment": assessment, "form": form})


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
