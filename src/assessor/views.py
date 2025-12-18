# src/assessor/views.py
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.utils.http import urlencode

from assessments.models import Assessment
from users.decorators import role_required


@login_required
@role_required(["teacher", "admin"])
def dashboard(request):
    # ─────────────────────────────────────────────
    # Pagination knobs (easy to tweak later)
    # ─────────────────────────────────────────────
    PER_PAGE = 25
    PAGE_PARAM = "page"

    # ─────────────────────────────────────────────
    # 1) Params (sort/search + toggles + pagination)
    # ─────────────────────────────────────────────
    sort = request.GET.get("sort", "submitted")
    direction = request.GET.get("dir", "desc")
    q = (request.GET.get("q") or "").strip()

    phone_only = request.GET.get("phone") == "1"
    active_only = request.GET.get("active") == "1"

    page_number = request.GET.get(PAGE_PARAM, "1")

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
        # show active only: must have evaluation and not archived
        qs = qs.filter(evaluation__isnull=False, evaluation__exam_archived=False)

    assessments = list(qs)

    # ─────────────────────────────────────────────
    # 3) Pre-compute helpers (for sorting + display)
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
    page_obj = paginator.get_page(page_number)
    assessments_page = list(page_obj.object_list)

    # ─────────────────────────────────────────────
    # 6) URL builders (preserve state)
    # ─────────────────────────────────────────────
    def base_params(include_page=True):
        params = {"sort": sort, "dir": direction}
        if q:
            params["q"] = q
        if phone_only:
            params["phone"] = "1"
        if active_only:
            params["active"] = "1"
        if include_page and page_obj.number != 1:
            params[PAGE_PARAM] = str(page_obj.number)
        return params

    # Mutually-exclusive toggles:
    # - when enabling phone, drop "active"
    # - when enabling active, drop "phone"
    phone_params = {"sort": sort, "dir": direction}
    if q:
        phone_params["q"] = q
    if not phone_only:
        phone_params["phone"] = "1"  # turning on phone-only
    # NOTE: do NOT carry "active" (mutual exclusion)
    toggle_phone_url = "?" + urlencode(phone_params)

    active_params = {"sort": sort, "dir": direction}
    if q:
        active_params["q"] = q
    if not active_only:
        active_params["active"] = "1"  # turning on active-only
    # NOTE: do NOT carry "phone" (mutual exclusion)
    toggle_active_url = "?" + urlencode(active_params)

    # Pagination base (keeps whichever toggle is currently active)
    pagination_base = base_params(include_page=False)

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
        "pagination_base_qs": urlencode(pagination_base),
        "per_page": PER_PAGE,
    }

    # ─────────────────────────────────────────────
    # 7) HTMX routing
    # ─────────────────────────────────────────────
    if request.headers.get("HX-Request", "").lower() == "true":
        # Return the whole card so toggles/search/pagination never disappear
        return render(request, "assessor/partials/teacher_assessments_card.html", context)

    return render(request, "assessor/dashboard.html", context)
