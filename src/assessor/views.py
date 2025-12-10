from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from assessments.models import Assessment
from users.decorators import role_required


@login_required
@role_required(["teacher", "admin"])
def dashboard(request):
    assessments = (
        Assessment.objects
        .select_related("user", "evaluation")
        .order_by("user__email")
    )

    # Pre-compute "Hhrs MMmins" label
    for a in assessments:
        ev = getattr(a, "evaluation", None)
        label = ""
        if ev and ev.completion_duration:
            total_seconds = int(ev.completion_duration.total_seconds())
            total_minutes = total_seconds // 60
            hours = total_minutes // 60
            minutes = total_minutes % 60

            # Always show "Hhrs MMmins" with 2-digit minutes
            label = f"{hours}hrs {minutes:02d}mins"

        a.evaluation_duration_label = label

    context = {
        "assessments": assessments,
    }
    return render(request, "assessor/dashboard.html", context)
