# src/assessor/views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from assessments.models import Assessment
from users.decorators import role_required


@login_required
@role_required(["teacher", "admin"])
def dashboard(request):
    # 1) Read sort parameters
    sort = request.GET.get("sort", "submitted")
    direction = request.GET.get("dir", "desc")

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

    # 2) Base queryset
    assessments = list(Assessment.objects.select_related("user", "evaluation"))

    # 3) Pre-compute helpers
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

    # 4) Sort key
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

    context = {
        "assessments": assessments,
        "active_sort": sort,
        "active_dir": direction,
    }

    # 5) htmx partial vs full page
    if request.headers.get("HX-Request", "").lower() == "true":
        # Only return the table HTML for htmx
        return render(request, "assessor/partials/assessment_table.html", context)

    # Full page for normal requests
    return render(request, "assessor/dashboard.html", context)
