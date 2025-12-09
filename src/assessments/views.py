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

from .forms import (
    ListeningAnswerForm,
    LLMQuestion1AnswerForm,
    LLMQuestion2AnswerForm,
    ReadingAnswerForm,
    WritingAnswerForm,
)
from .llm_client import get_openai_client
from .models import Assessment, AssessmentEvaluation, DebateTopic
from .services.evaluation import generate_evaluation_for_assessment
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
    - Handles follow-up question 1 and 2 (draft + submit/lock).
    - Handles listening comprehension (draft + submit/lock).
    - Handles reading comprehension (draft + submit/lock).
    - Ensures each Assessment is assigned a random reading debate topic.
    - For HTMX submits on writing, avoids full-page redirects (returns 204).
    """

    # Each user gets exactly one Assessment row (created on first visit).
    assessment, _ = Assessment.objects.get_or_create(user=request.user)

    # ─────────────────────────────────────────────────────────────────────
    # Ensure a reading debate is assigned as soon as the Assessment exists.
    #
    # We:
    # - Pick a random active DebateTopic (if any exist).
    # - Only assign it once per Assessment.
    # - Use PROTECT on the FK so topics cannot be deleted while in use.
    # This keeps reading_debate stable for the lifetime of the Assessment.
    # ─────────────────────────────────────────────────────────────────────
    if assessment.reading_debate is None:
        debate = DebateTopic.objects.filter(is_active=True).order_by("?").first()
        if debate is not None:
            assessment.reading_debate = debate
            assessment.save(update_fields=["reading_debate"])

    writing_locked = bool(assessment.writing_answer_final)
    is_hx = "HX-Request" in request.headers

    # ── Pre-build follow-up forms for GET / non-own POST paths ─────────────
    # Q1: only if a question exists
    llm_q1_form = None
    if assessment.llm_question_1:
        llm_q1_form = LLMQuestion1AnswerForm(
            initial={"llm_question_1_answer": assessment.llm_question_1_answer_draft}
        )

    # Q2: only if a question exists
    llm_q2_form = None
    if assessment.llm_question_2:
        llm_q2_form = LLMQuestion2AnswerForm(
            initial={"llm_question_2_answer": assessment.llm_question_2_answer_draft}
        )

    # Listening: only if Q2 final exists and listening not yet final
    listening_form = None
    if assessment.llm_question_2_answer_final and not assessment.listening_answer_final:
        listening_form = ListeningAnswerForm(
            initial={"listening_answer": assessment.listening_answer_draft}
        )

    # Reading: only if listening final exists, a debate is assigned,
    # and reading answer is not yet final
    reading_form = None
    if (
        assessment.listening_answer_final
        and assessment.reading_debate
        and not assessment.reading_answer_final
    ):
        reading_form = ReadingAnswerForm(
            initial={"reading_answer": assessment.reading_answer_draft}
        )

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()

        # ─────────────────────────────────────────────────────────────────────
        # Follow-up Question 1: save / submit
        # ─────────────────────────────────────────────────────────────────────
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

            # Bind Q1 form from POST
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
                        "llm_q2_form": llm_q2_form,
                        "listening_form": listening_form,
                        "reading_form": reading_form,
                    },
                )

            q1_answer = llm_q1_form.cleaned_data.get("llm_question_1_answer") or ""
            MAX_CHARS = 3000  # keep in sync with client-side

            # Draft path: no word-limit enforcement
            if action == "q1_save":
                assessment.llm_question_1_answer_draft = q1_answer[:MAX_CHARS]
                assessment.save(update_fields=["llm_question_1_answer_draft", "updated_at"])
                messages.success(request, "Follow-up question 1 draft saved.")
                return redirect("assessments:home")

            # Submit path: enforce 250–300 words, then lock
            MIN_W, MAX_W = 250, 300
            n_words = _count_words(q1_answer)

            if n_words < MIN_W or n_words > MAX_W:
                # Keep latest draft; do not lock
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
                        "llm_q2_form": llm_q2_form,
                        "listening_form": listening_form,
                        "reading_form": reading_form,
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

        # ─────────────────────────────────────────────────────────────────────
        # Follow-up Question 2: save / submit
        # ─────────────────────────────────────────────────────────────────────
        if action in {"q2_save", "q2_submit"}:
            # Q2 only makes sense if:
            # - The Q2 prompt exists AND
            # - The Q1 answer has been fully submitted
            if not assessment.llm_question_2 or not assessment.llm_question_1_answer_final:
                messages.error(
                    request,
                    "Follow-up question 2 is not available yet.",
                )
                return redirect("assessments:home")

            # Once final is set, ignore further edits
            if assessment.llm_question_2_answer_final:
                messages.info(
                    request,
                    "Your answer to follow-up question 2 has already been submitted.",
                )
                return redirect("assessments:home")

            # Bind Q2 form from POST
            llm_q2_form = LLMQuestion2AnswerForm(request.POST)
            if not llm_q2_form.is_valid():
                messages.error(request, "Please check your answer and try again.")
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
                        "llm_q2_form": llm_q2_form,
                        "listening_form": listening_form,
                        "reading_form": reading_form,
                    },
                )

            q2_answer = llm_q2_form.cleaned_data.get("llm_question_2_answer") or ""
            MAX_CHARS = 3000  # keep in sync with client-side

            # Draft path: no word-limit enforcement
            if action == "q2_save":
                assessment.llm_question_2_answer_draft = q2_answer[:MAX_CHARS]
                assessment.save(update_fields=["llm_question_2_answer_draft", "updated_at"])
                messages.success(request, "Follow-up question 2 draft saved.")
                return redirect("assessments:home")

            # Submit path: enforce 250–300 words, then lock
            MIN_W, MAX_W = 250, 300
            n_words = _count_words(q2_answer)

            if n_words < MIN_W or n_words > MAX_W:
                # Keep latest draft; do not lock
                assessment.llm_question_2_answer_draft = q2_answer[:MAX_CHARS]
                assessment.save(update_fields=["llm_question_2_answer_draft", "updated_at"])
                messages.error(
                    request,
                    (
                        f"Your answer to follow-up question 2 is {n_words} words. "
                        f"It must be between {MIN_W} and {MAX_W} words to submit."
                    ),
                )
                # Rebuild forms with latest draft values
                llm_q2_form = LLMQuestion2AnswerForm(
                    initial={"llm_question_2_answer": assessment.llm_question_2_answer_draft}
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
                        "llm_q2_form": llm_q2_form,
                        "listening_form": listening_form,
                        "reading_form": reading_form,
                    },
                )

            # ✅ Lock Q2 answer
            assessment.llm_question_2_answer_draft = q2_answer[:MAX_CHARS]
            assessment.llm_question_2_answer_final = assessment.llm_question_2_answer_draft
            assessment.llm_question_2_answer_submitted_at = timezone.now()
            assessment.save(
                update_fields=[
                    "llm_question_2_answer_draft",
                    "llm_question_2_answer_final",
                    "llm_question_2_answer_submitted_at",
                    "updated_at",
                ]
            )

            messages.success(
                request,
                "Your answer to follow-up question 2 has been submitted.",
            )
            # 🔜 Future: trigger LLM Q3 generation here if needed
            return redirect("assessments:home")

        # ─────────────────────────────────────────────────────────────────────
        # Listening comprehension: save / submit
        # ─────────────────────────────────────────────────────────────────────
        if action in {"listening_save", "listening_submit"}:
            # Listening only makes sense if:
            # - Q2 has a final answer
            if not assessment.llm_question_2_answer_final:
                messages.error(
                    request,
                    "The listening exercise is not available yet.",
                )
                return redirect("assessments:home")

            # Once final is set, ignore further edits
            if assessment.listening_answer_final:
                messages.info(
                    request,
                    "Your listening answer has already been submitted.",
                )
                return redirect("assessments:home")

            # Bind listening form from POST
            listening_form = ListeningAnswerForm(request.POST)
            if not listening_form.is_valid():
                messages.error(request, "Please check your answer and try again.")
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
                        "llm_q2_form": llm_q2_form,
                        "listening_form": listening_form,
                        "reading_form": reading_form,
                    },
                )

            listening_answer = listening_form.cleaned_data.get("listening_answer") or ""
            MAX_CHARS = 3000  # keep in sync with client-side

            # Draft path: no word-limit enforcement
            if action == "listening_save":
                assessment.listening_answer_draft = listening_answer[:MAX_CHARS]
                assessment.save(update_fields=["listening_answer_draft", "updated_at"])
                messages.success(request, "Listening draft saved.")
                return redirect("assessments:home")

            # Submit path: enforce 250–300 words, then lock
            MIN_W, MAX_W = 250, 300
            n_words = _count_words(listening_answer)

            if n_words < MIN_W or n_words > MAX_W:
                # Keep latest draft; do not lock
                assessment.listening_answer_draft = listening_answer[:MAX_CHARS]
                assessment.save(update_fields=["listening_answer_draft", "updated_at"])
                messages.error(
                    request,
                    (
                        f"Your listening summary is {n_words} words. "
                        f"It must be between {MIN_W} and {MAX_W} words to submit."
                    ),
                )
                # Rebuild forms with latest draft values
                listening_form = ListeningAnswerForm(
                    initial={"listening_answer": assessment.listening_answer_draft}
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
                        "llm_q2_form": llm_q2_form,
                        "listening_form": listening_form,
                        "reading_form": reading_form,
                    },
                )

            # ✅ Lock listening answer
            assessment.listening_answer_draft = listening_answer[:MAX_CHARS]
            assessment.listening_answer_final = assessment.listening_answer_draft
            assessment.listening_answer_submitted_at = timezone.now()
            assessment.save(
                update_fields=[
                    "listening_answer_draft",
                    "listening_answer_final",
                    "listening_answer_submitted_at",
                    "updated_at",
                ]
            )

            messages.success(
                request,
                "Your listening answer has been submitted.",
            )
            return redirect("assessments:home")

        # ─────────────────────────────────────────────────────────────────────
        # Reading comprehension: save / submit
        # ─────────────────────────────────────────────────────────────────────
        if action in {"reading_save", "reading_submit"}:
            # Reading only makes sense if:
            # - The listening summary has a final answer AND
            # - A DebateTopic has been assigned
            if not assessment.listening_answer_final or not assessment.reading_debate:
                messages.error(
                    request,
                    "The reading exercise is not available yet.",
                )
                return redirect("assessments:home")

            # Once final is set, ignore further edits
            if assessment.reading_answer_final:
                messages.info(
                    request,
                    "Your reading answer has already been submitted.",
                )
                return redirect("assessments:home")

            # Bind reading form from POST
            reading_form = ReadingAnswerForm(request.POST)
            if not reading_form.is_valid():
                messages.error(request, "Please check your answer and try again.")
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
                        "llm_q2_form": llm_q2_form,
                        "listening_form": listening_form,
                        "reading_form": reading_form,
                    },
                )

            reading_answer = reading_form.cleaned_data.get("reading_answer") or ""
            MAX_CHARS = 3000  # keep in sync with client-side

            # Draft path: no word-limit enforcement
            if action == "reading_save":
                assessment.reading_answer_draft = reading_answer[:MAX_CHARS]
                assessment.save(update_fields=["reading_answer_draft", "updated_at"])
                messages.success(request, "Reading draft saved.")
                return redirect("assessments:home")

            # Submit path: enforce 250–300 words, then lock
            MIN_W, MAX_W = 250, 300
            n_words = _count_words(reading_answer)

            if n_words < MIN_W or n_words > MAX_W:
                # Keep latest draft; do not lock
                assessment.reading_answer_draft = reading_answer[:MAX_CHARS]
                assessment.save(update_fields=["reading_answer_draft", "updated_at"])
                messages.error(
                    request,
                    (
                        f"Your reading answer is {n_words} words. "
                        f"It must be between {MIN_W} and {MAX_W} words to submit."
                    ),
                )
                # Rebuild forms with latest draft values
                reading_form = ReadingAnswerForm(
                    initial={"reading_answer": assessment.reading_answer_draft}
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
                        "llm_q2_form": llm_q2_form,
                        "listening_form": listening_form,
                        "reading_form": reading_form,
                    },
                )

            # ✅ Lock reading answer
            assessment.reading_answer_draft = reading_answer[:MAX_CHARS]
            assessment.reading_answer_final = assessment.reading_answer_draft
            assessment.reading_answer_submitted_at = timezone.now()
            assessment.save(
                update_fields=[
                    "reading_answer_draft",
                    "reading_answer_final",
                    "reading_answer_submitted_at",
                    "updated_at",
                ]
            )

            # After reading is locked and saved
            if assessment.is_fully_complete:
                # Avoid duplicates
                if not hasattr(assessment, "evaluation"):
                    # Get profile for USN
                    profile = Profile.objects.filter(user=request.user).first()
                    usn = getattr(profile, "student_number", "") if profile else ""

                    submitted_at = assessment.reading_answer_submitted_at
                    completion_duration = assessment.completion_duration

                    evaluation = AssessmentEvaluation.objects.create(
                        assessment=assessment,
                        student_email=request.user.email,
                        student_usn=usn,
                        submitted_at=submitted_at,
                        completion_duration=completion_duration,
                    )

                    # here we'll call the LLM evaluation service
                    # Call LLM to generate the evaluation text
                    eval_text, error, model_name = generate_evaluation_for_assessment(assessment)

                    if eval_text:
                        evaluation.llm_evaluation_text = eval_text
                        evaluation.llm_model_name = model_name
                        evaluation.llm_generated_at = timezone.now()
                        evaluation.llm_error = ""
                        evaluation.save(
                            update_fields=[
                                "llm_evaluation_text",
                                "llm_model_name",
                                "llm_generated_at",
                                "llm_error",
                                "updated_at",
                            ]
                        )
                    elif error:
                        evaluation.llm_error = error
                        evaluation.llm_model_name = model_name
                        evaluation.save(
                            update_fields=[
                                "llm_error",
                                "llm_model_name",
                                "updated_at",
                            ]
                        )

            messages.success(
                request,
                "Your reading answer has been submitted.",
            )

            return redirect("users:student_home")

        # ─────────────────────────────────────────────────────────────────────
        # Writing: save / submit
        # ─────────────────────────────────────────────────────────────────────
        # Short-circuit: once writing is locked, ignore further save/submit attempts
        if writing_locked and action in {"save", "submit"}:
            messages.info(
                request,
                "Your writing answer has already been submitted and cannot be changed.",
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
                    "llm_q2_form": llm_q2_form,
                    "listening_form": listening_form,
                    "reading_form": reading_form,
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
                        "llm_q2_form": llm_q2_form,
                        "listening_form": listening_form,
                        "reading_form": reading_form,
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

            # LLM follow-up generation (Q1 + Q2 prompts)
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

        # ─────────────────────────────────────────────────────────────────────
        # Fallback: unknown action
        # ─────────────────────────────────────────────────────────────────────
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
                "llm_q2_form": llm_q2_form,
                "listening_form": listening_form,
                "reading_form": reading_form,
            },
        )

    # ─────────────────────────────────────────────────────────────────────────
    # GET: prefill writing form with current draft
    # ─────────────────────────────────────────────────────────────────────────
    form = WritingAnswerForm(initial={"writing_answer": assessment.writing_answer_draft})
    return render(
        request,
        "assessments/home.html",
        {
            "assessment": assessment,
            "form": form,
            "writing_locked": writing_locked,
            "llm_q1_form": llm_q1_form,
            "llm_q2_form": llm_q2_form,
            "listening_form": listening_form,
            "reading_form": reading_form,
        },
    )
