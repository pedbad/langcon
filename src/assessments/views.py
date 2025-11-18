# src/assessments/views.py

# Django imports
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

# Local app imports
from profiles.models import Profile
from profiles.utils import require_complete_profile

from .forms import LLMQuestion1AnswerForm, WritingAnswerForm
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


@login_required
@require_complete_profile
def home(request):
    """
    Assessment main view:
    - Shows the writing prompt and answer form.
    - Allows students to save drafts (even empty) while unlocked.
    - Enforces submit rules (250–300 words), locks final answer on submit.
    - Once the writing answer is locked, ignores further save/submit attempts.
    - Handles follow-up question 1 (draft + submit/lock).
    - For HTMX submits on writing, avoids full-page redirects.
    """

    assessment, _ = Assessment.objects.get_or_create(user=request.user)
    writing_locked = bool(assessment.writing_answer_final)
    is_hx = "HX-Request" in request.headers

    # Pre-build Q1 form (unbound) for GET / non-Q1 POST paths
    llm_q1_form = None
    if assessment.llm_question_1:
        llm_q1_form = LLMQuestion1AnswerForm(
            initial={"llm_question_1_answer": assessment.llm_question_1_answer_draft}
        )

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        # ── Follow-up Question 1: save / submit ─────────────────────────────
        if action in {"q1_save", "q1_submit"}:
            # Must have an LLM question before allowing answers
            if not assessment.llm_question_1:
                messages.error(
                    request,
                    "Follow-up question 1 is not available yet.",
                )
                return redirect("assessments:home")

            # Once final is set, ignore further edits
            if assessment.llm_question_1_answer_final:
                messages.info(
                    request,
                    "Your answer to follow-up question 1 has already been submitted.",
                )
                return redirect("assessments:home")

            llm_q1_form = LLMQuestion1AnswerForm(request.POST)
            if not llm_q1_form.is_valid():
                messages.error(request, "Please check your answer and try again.")
                # Writing form: use current draft (locked or not)
                form = WritingAnswerForm(
                    initial={"writing_answer": assessment.writing_answer_draft}
                )
                return render(
                    request,
                    "assessments/home.html",
                    {
                        "assessment": assessment,
                        "form": form,
                        "writing_locked": writing_locked,
                        "llm_q1_form": llm_q1_form,
                    },
                )

            q1_answer = llm_q1_form.cleaned_data.get("llm_question_1_answer") or ""
            MAX_CHARS = 3000  # keep in sync with client-side

            if action == "q1_save":
                # Draft only, no word limit enforcement
                assessment.llm_question_1_answer_draft = q1_answer[:MAX_CHARS]
                assessment.save(update_fields=["llm_question_1_answer_draft", "updated_at"])
                messages.success(request, "Follow-up question 1 draft saved.")
                return redirect("assessments:home")

            # action == "q1_submit": enforce word range and lock
            MIN_W, MAX_W = 250, 300
            n_words = _count_words(q1_answer)

            if n_words < MIN_W or n_words > MAX_W:
                assessment.llm_question_1_answer_draft = q1_answer[:MAX_CHARS]
                assessment.save(update_fields=["llm_question_1_answer_draft", "updated_at"])
                messages.error(
                    request,
                    (
                        f"Your answer to follow-up question 1 is {n_words} words. "
                        f"It must be between {MIN_W} and {MAX_W} words to submit."
                    ),
                )
                # Rebuild forms with latest draft values
                llm_q1_form = LLMQuestion1AnswerForm(
                    initial={"llm_question_1_answer": assessment.llm_question_1_answer_draft}
                )
                form = WritingAnswerForm(
                    initial={"writing_answer": assessment.writing_answer_draft}
                )
                return render(
                    request,
                    "assessments/home.html",
                    {
                        "assessment": assessment,
                        "form": form,
                        "writing_locked": writing_locked,
                        "llm_q1_form": llm_q1_form,
                    },
                )

            # ✅ Lock Q1 answer
            assessment.llm_question_1_answer_draft = q1_answer[:MAX_CHARS]
            assessment.llm_question_1_answer_final = assessment.llm_question_1_answer_draft
            assessment.llm_question_1_answer_submitted_at = timezone.now()
            assessment.save(
                update_fields=[
                    "llm_question_1_answer_draft",
                    "llm_question_1_answer_final",
                    "llm_question_1_answer_submitted_at",
                    "updated_at",
                ]
            )

            messages.success(
                request,
                "Your answer to follow-up question 1 has been submitted.",
            )
            return redirect("assessments:home")

        # ── Writing: save / submit ──────────────────────────────────────────
        # Short-circuit: once writing is locked, ignore further save/submit attempts
        if writing_locked and action in {"save", "submit"}:
            messages.info(
                request,
                ("Your writing answer has already been submitted and " "cannot be changed."),
            )
            if is_hx:
                # HTMX: no redirect; frontend stays on the current page
                return HttpResponse(status=204)
            return redirect("assessments:home")

        # Common form binding for both writing actions (only if not locked)
        form = WritingAnswerForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Please check your input and try again.")
            return render(
                request,
                "assessments/home.html",
                {
                    "assessment": assessment,
                    "form": form,
                    "writing_locked": writing_locked,
                    "llm_q1_form": llm_q1_form,
                },
            )

        answer = form.cleaned_data.get("writing_answer") or ""

        # Soft-cap safety for drafts (matches client maxlength)
        MAX_CHARS = 3000  # ≈ 500 words (client has maxlength="3000")
        if action == "save":
            if len(answer) > MAX_CHARS:
                # Truncate on server to avoid huge payloads; warn user.
                assessment.writing_answer_draft = answer[:MAX_CHARS]
                assessment.save(update_fields=["writing_answer_draft", "updated_at"])
                messages.warning(
                    request,
                    (
                        f"Draft truncated to {MAX_CHARS} characters "
                        "(≈500 words). Please shorten your answer."
                    ),
                )
            else:
                assessment.writing_answer_draft = answer
                assessment.save(update_fields=["writing_answer_draft", "updated_at"])
                messages.success(request, "Draft saved.")

            if is_hx:
                return HttpResponse(status=204)
            return redirect("assessments:home")  # PRG

        # Submit path: enforce policy and lock
        if action == "submit":
            # Defensive: if it became locked between get_or_create and now
            if assessment.writing_answer_final:
                messages.info(request, "Your writing answer is already submitted.")
                if is_hx:
                    return HttpResponse(status=204)
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
                        f"Your answer is {n_words} words. It must be between "
                        f"{MIN_W} and {MAX_W} words to submit."
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
                        "writing_locked": False,  # still unlocked if validation failed
                        "llm_q1_form": llm_q1_form,
                    },
                )

            # ✅ Lock: copy draft → final and timestamp
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

            # LLM follow-up generation
            try:
                data = generate_followups_from_statement(assessment.writing_answer_final)
                q1 = (data.get("question1") or "").strip()
                q2 = (data.get("question2") or "").strip()
                if not q1 or not q2:
                    raise ValueError("Missing question1/question2 in LLM response")

                assessment.llm_question_1 = q1
                assessment.llm_question_2 = q2
                assessment.save(
                    update_fields=[
                        "llm_question_1",
                        "llm_question_2",
                        "updated_at",
                    ]
                )

                messages.success(
                    request,
                    "Submitted. Your first follow-up question is ready.",
                )
            except Exception:
                messages.warning(
                    request,
                    (
                        "Submitted. We’re preparing your follow-up questions, but there "
                        "was a hiccup. Please refresh shortly or try again later."
                    ),
                )

            if is_hx:
                return HttpResponse(status=204)
            return redirect("assessments:home")

        # Unknown action
        messages.error(request, "Unknown action.")
        form = WritingAnswerForm(initial={"writing_answer": assessment.writing_answer_draft})
        return render(
            request,
            "assessments/home.html",
            {
                "assessment": assessment,
                "form": form,
                "writing_locked": writing_locked,
                "llm_q1_form": llm_q1_form,
            },
        )

    # GET: prefill form with current draft
    form = WritingAnswerForm(initial={"writing_answer": assessment.writing_answer_draft})
    return render(
        request,
        "assessments/home.html",
        {
            "assessment": assessment,
            "form": form,
            "writing_locked": writing_locked,
            "llm_q1_form": llm_q1_form,
        },
    )
