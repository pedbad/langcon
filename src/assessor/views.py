# src/assessor/views.py
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import urlencode

from assessments.models import Assessment
from users.decorators import role_required
from users.models import User

from .forms import AssessmentEvaluationDecisionForm

# ─────────────────────────────────────────────
# Pagination constants (easy to tweak later)
# ─────────────────────────────────────────────
PER_PAGE = 25
PAGE_PARAM = "page"


@login_required
@role_required(["teacher", "admin"])
def dashboard(request):
    # ─────────────────────────────────────────────
    # 0) Top-card quick stats (all student users)
    # ─────────────────────────────────────────────
    total_assessments = 0
    not_started_count = 0
    in_progress_count = 0
    completed_count = 0
    marked_count = 0

    student_users = User.objects.filter(role=User.Roles.STUDENT).select_related("assessment")
    for student in student_users:
        try:
            assessment = student.assessment
        except Exception:  # noqa: BLE001
            assessment = None

        if assessment is None:
            continue

        total_assessments += 1
        if assessment.steps_completed == 0:
            not_started_count += 1
        elif assessment.is_fully_complete:
            completed_count += 1
        elif assessment.steps_completed > 0:
            in_progress_count += 1

        ev = getattr(assessment, "evaluation", None)
        if ev and ev.exam_marked:
            marked_count += 1

    not_completed_count = total_assessments - completed_count
    left_to_mark_count = total_assessments - marked_count

    # ─────────────────────────────────────────────
    # 1) Params (sort/search + toggles + page)
    # ─────────────────────────────────────────────
    sort = request.GET.get("sort", "submitted")
    direction = request.GET.get("dir", "desc")
    q = (request.GET.get("q") or "").strip()

    phone_only = request.GET.get("phone") == "1"
    active_only = request.GET.get("active") == "1"

    page = request.GET.get(PAGE_PARAM, "1")

    valid_sorts = {
        "student",
        "usn",
        "status",
        "submitted",
        "recommendation",
        "exam_marked",
        "phone_follow_up",
        "archive_status",
    }
    if sort not in valid_sorts:
        sort = "submitted"
    if direction not in ("asc", "desc"):
        direction = "desc"
    reverse = direction == "desc"

    # ─────────────────────────────────────────────
    # 2) Base queryset (students only)
    # ─────────────────────────────────────────────
    qs = Assessment.objects.select_related("user", "evaluation").filter(user__role="student")

    if q:
        qs = qs.filter(
            Q(user__email__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(evaluation__student_usn__icontains=q)
            | Q(evaluation__student_email__icontains=q)
        )

    # Toggle filters
    if phone_only:
        qs = qs.filter(evaluation__phone_follow_up=True)

    if active_only:
        qs = qs.filter(evaluation__isnull=False, evaluation__exam_archived=False)

    assessments = list(qs)

    # ─────────────────────────────────────────────
    # 3) Pre-compute helpers
    # ─────────────────────────────────────────────
    for a in assessments:
        ev = getattr(a, "evaluation", None)

        # Duration label
        label = ""
        if ev and ev.completion_duration:
            total_seconds = int(ev.completion_duration.total_seconds())
            total_minutes = total_seconds // 60
            hours = total_minutes // 60
            minutes = total_minutes % 60
            label = f"{hours}hrs {minutes:02d}mins"
        a.evaluation_duration_label = label

        # Student email for sorting
        if ev and ev.student_email:
            student_email = ev.student_email
        elif a.user and a.user.email:
            student_email = a.user.email
        else:
            student_email = ""
        a.sort_student = student_email.lower()

        # USN
        a.sort_usn = ev.student_usn if ev and ev.student_usn else ""

        # Submitted
        if ev and ev.submitted_at:
            a.sort_submitted = (0, ev.submitted_at)
        else:
            a.sort_submitted = (1, None)

        # Recommendation
        a.sort_recommendation = ev.recommendation if ev and ev.recommendation else ""

        # Booleans
        a.sort_exam_marked = 1 if (ev and ev.exam_marked) else 0
        a.sort_phone_follow_up = 1 if (ev and ev.phone_follow_up) else 0

        # Archive: 0 = active, 1 = archived, 2 = no evaluation
        if ev is None:
            a.sort_archive = 2
        else:
            a.sort_archive = 1 if ev.exam_archived else 0

        # Status + progress
        if a.is_fully_complete:
            status_rank = 0  # Completed
        elif a.steps_completed > 0:
            status_rank = 1  # In progress
        else:
            status_rank = 2  # Not started
        a.sort_status_rank = status_rank

        try:
            a.sort_progress_pct = int(a.progress_pct)
        except Exception:
            a.sort_progress_pct = 0

    # ─────────────────────────────────────────────
    # 4) Sort key
    # ─────────────────────────────────────────────
    def sort_key(a):
        if sort == "student":
            return a.sort_student
        if sort == "usn":
            return a.sort_usn
        if sort == "status":
            # closest to finish (higher % first) within "in progress"
            return (a.sort_status_rank, -a.sort_progress_pct)
        if sort == "submitted":
            return a.sort_submitted
        if sort == "recommendation":
            return a.sort_recommendation
        if sort == "exam_marked":
            return a.sort_exam_marked
        if sort == "phone_follow_up":
            return a.sort_phone_follow_up
        if sort == "archive_status":
            return a.sort_archive
        return a.sort_student

    assessments = sorted(assessments, key=sort_key, reverse=reverse)

    # ─────────────────────────────────────────────
    # 5) Pagination (after sorting)
    # ─────────────────────────────────────────────
    paginator = Paginator(assessments, PER_PAGE)
    try:
        page_obj = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    assessments_page = list(page_obj.object_list)

    # ─────────────────────────────────────────────
    # 6) Querystring helpers (preserve state)
    # ─────────────────────────────────────────────
    base_params = {
        "sort": sort,
        "dir": direction,
    }
    if q:
        base_params["q"] = q
    if phone_only:
        base_params["phone"] = "1"
    if active_only:
        base_params["active"] = "1"

    base_qs = urlencode(base_params)  # no page param on purpose

    # ─────────────────────────────────────────────
    # 7) Toggle URLs (mutually exclusive: phone vs active)
    # ─────────────────────────────────────────────
    # Phone toggle: if currently ON -> turn OFF (remove phone)
    # if currently OFF -> turn ON AND turn OFF active
    phone_params = dict(base_params)
    phone_params.pop(PAGE_PARAM, None)
    if phone_only:
        phone_params.pop("phone", None)
    else:
        phone_params["phone"] = "1"
        phone_params.pop("active", None)  # <-- mutual exclusion
    toggle_phone_url = "?" + urlencode(phone_params)

    # Active toggle: if currently ON -> turn OFF (remove active)
    # if currently OFF -> turn ON AND turn OFF phone
    active_params = dict(base_params)
    active_params.pop(PAGE_PARAM, None)
    if active_only:
        active_params.pop("active", None)
    else:
        active_params["active"] = "1"
        active_params.pop("phone", None)  # <-- mutual exclusion
    toggle_active_url = "?" + urlencode(active_params)

    context = {
        "assessments": assessments_page,
        "active_sort": sort,
        "active_dir": direction,
        "search_query": q,
        "phone_only": phone_only,
        "active_only": active_only,
        "toggle_phone_url": toggle_phone_url,
        "toggle_active_url": toggle_active_url,
        "page_obj": page_obj,
        "paginator": paginator,
        "base_qs": base_qs,
        "per_page": PER_PAGE,
        "dashboard_stats": {
            "total_assessments": total_assessments,
            "not_started": not_started_count,
            "in_progress": in_progress_count,
            "not_completed": not_completed_count,
            "marked": marked_count,
            "left_to_mark": left_to_mark_count,
        },
    }

    # ─────────────────────────────────────────────
    # 8) HTMX routing
    # ─────────────────────────────────────────────
    if request.headers.get("HX-Request", "").lower() == "true":
        return render(request, "assessor/partials/teacher_assessments_card.html", context)

    return render(request, "assessor/dashboard.html", context)


@login_required
@role_required(["admin"])
def students(request):
    """
    Admin-only student registry:
    - includes all student users, even if profile/assessment is incomplete/missing
    - supports basic search and pagination
    """
    q = (request.GET.get("q") or "").strip()
    sort = request.GET.get("sort", "joined")
    direction = request.GET.get("dir", "desc")
    year_raw = (request.GET.get("year") or "").strip()
    page = request.GET.get(PAGE_PARAM, "1")
    valid_sorts = {"student", "usn", "profile", "assessment", "joined"}
    if sort not in valid_sorts:
        sort = "joined"
    if direction not in ("asc", "desc"):
        direction = "desc"
    reverse = direction == "desc"

    all_students_qs = User.objects.filter(role=User.Roles.STUDENT)
    years = [d.year for d in all_students_qs.dates("date_joined", "year", order="DESC")]
    year_counts = {year: all_students_qs.filter(date_joined__year=year).count() for year in years}
    year_chips = [{"year": year, "count": year_counts[year]} for year in years]
    total_students_all_years = sum(year_counts.values())

    selected_year = None
    if year_raw.isdigit():
        year_candidate = int(year_raw)
        if year_candidate in years:
            selected_year = year_candidate

    qs = all_students_qs.select_related("profile", "assessment")
    if selected_year:
        qs = qs.filter(date_joined__year=selected_year)
    if q:
        qs = qs.filter(
            Q(email__icontains=q)
            | Q(first_name__icontains=q)
            | Q(last_name__icontains=q)
            | Q(profile__student_number__icontains=q)
        )

    student_rows = []
    for student in qs:
        try:
            profile = student.profile
        except Exception:  # noqa: BLE001
            profile = None
        try:
            assessment = student.assessment
        except Exception:  # noqa: BLE001
            assessment = None
        if assessment:
            try:
                evaluation = assessment.evaluation
            except Exception:  # noqa: BLE001
                evaluation = None
        else:
            evaluation = None

        display_name = student.get_full_name() or "—"
        profile_complete = bool(profile and profile.is_complete())
        has_assessment = bool(assessment)
        if assessment and assessment.is_fully_complete:
            assessment_state = "completed"
            assessment_status = "Completed"
        elif assessment and assessment.steps_completed > 0:
            assessment_state = "in_progress"
            assessment_status = assessment.status_label
        else:
            assessment_state = "not_started"
            assessment_status = "Not started"
        is_marked = bool(evaluation and evaluation.exam_marked)

        student_number_value = (getattr(profile, "student_number", "") if profile else "") or ""
        assessment_status_sort = (assessment_status or "").lower()

        student_rows.append(
            {
                "user": student,
                "display_name": display_name,
                "email": student.email,
                "student_number": student_number_value,
                "profile_complete": profile_complete,
                "profile_state": "completed" if profile_complete else "not_started",
                "assessment_status": assessment_status,
                "has_assessment": has_assessment,
                "assessment_state": assessment_state,
                "is_marked": is_marked,
                "date_joined": student.date_joined,
                "sort_student": (display_name or student.email or "").lower(),
                "sort_usn": str(student_number_value).lower(),
                "sort_profile": 1 if profile_complete else 0,
                "sort_assessment": (
                    0 if has_assessment else 1,
                    assessment_status_sort,
                ),
            }
        )

    def sort_key(row):
        if sort == "student":
            return row["sort_student"]
        if sort == "usn":
            return row["sort_usn"]
        if sort == "profile":
            return row["sort_profile"]
        if sort == "assessment":
            return row["sort_assessment"]
        if sort == "joined":
            return row["date_joined"]
        return row["date_joined"]

    student_rows = sorted(student_rows, key=sort_key, reverse=reverse)

    total_students = len(student_rows)
    profile_complete_count = sum(1 for row in student_rows if row["profile_complete"])
    profile_incomplete_count = total_students - profile_complete_count
    assessment_created_count = sum(1 for row in student_rows if row["has_assessment"])
    no_assessment_count = total_students - assessment_created_count
    marked_count = sum(1 for row in student_rows if row["is_marked"])
    left_to_mark_count = assessment_created_count - marked_count

    paginator = Paginator(student_rows, PER_PAGE)
    try:
        page_obj = paginator.page(page)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.page(1)

    base_params = {"sort": sort, "dir": direction}
    if q:
        base_params["q"] = q
    if selected_year:
        base_params["year"] = str(selected_year)
    base_qs = urlencode(base_params)

    return render(
        request,
        "assessor/students.html",
        {
            "student_rows": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "search_query": q,
            "per_page": PER_PAGE,
            "active_sort": sort,
            "active_dir": direction,
            "base_qs": base_qs,
            "years": years,
            "year_chips": year_chips,
            "year_counts": year_counts,
            "total_students_all_years": total_students_all_years,
            "selected_year": selected_year,
            "students_stats": {
                "total_students": total_students,
                "profile_complete": profile_complete_count,
                "profile_incomplete": profile_incomplete_count,
                "assessment_created": assessment_created_count,
                "no_assessment": no_assessment_count,
                "marked": marked_count,
                "left_to_mark": left_to_mark_count,
            },
        },
    )


@login_required
@role_required(["teacher", "admin"])
def student_detail(request, assessment_id):
    assessment = get_object_or_404(
        Assessment.objects.select_related("user", "evaluation"),
        id=assessment_id,
        user__role="student",
    )

    ev = getattr(assessment, "evaluation", None)

    # Duration label (safe)
    label = ""
    if ev and ev.completion_duration:
        total_seconds = int(ev.completion_duration.total_seconds())
        total_minutes = total_seconds // 60
        hours = total_minutes // 60
        minutes = total_minutes % 60
        label = f"{hours}hrs {minutes:02d}mins"
    assessment.evaluation_duration_label = label

    # Strict rule: do not allow saving without a real evaluation
    if request.method == "POST":
        if ev is None:
            messages.error(
                request,
                "This assessment has no evaluation yet. "
                "You can only save recommendations/comments after submission.",
            )
            return redirect("assessor:student_detail", assessment_id=assessment.id)

        form = AssessmentEvaluationDecisionForm(request.POST, instance=ev)
        if form.is_valid():
            saved = form.save(commit=False)

            # Optional: keep email snapshot aligned (safe)
            saved.student_email = assessment.user.email or saved.student_email

            saved.assessor = request.user
            saved.assessor_reviewed_at = timezone.now()

            saved.save()
            messages.success(request, "Assessor decision saved.")
            return redirect("assessor:student_detail", assessment_id=assessment.id)
    else:
        form = AssessmentEvaluationDecisionForm(instance=ev) if ev else None

    context = {
        "assessment": assessment,
        "ev": ev,
        "student_name": assessment.user.get_full_name() or "—",
        "student_email": assessment.user.email or "—",
        "decision_form": form,  # None when no evaluation exists
    }
    return render(request, "assessor/student_detail.html", context)
