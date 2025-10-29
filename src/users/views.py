# users/views.py

# Django imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractBaseUser
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse, reverse_lazy
from django.views.generic import CreateView

# Local imports
from .constants import PWD_RESET_TPLS  # ← centralised template names
from .decorators import role_required
from .forms import RegisterForm
from .mixins import AdminRequiredMixin

User = get_user_model()


def _redirect_for_role(user: AbstractBaseUser) -> str:
    """
    Map user.role → URL name, with sane fallbacks and support for @override_settings.
    Priority:
      1) settings.USERS_ROLE_REDIRECTS (if provided in runtime/tests)
      2) sensible defaults for known roles (admin/teacher/student)
    """
    role = getattr(user, "role", None)

    # 1) Honor dynamic settings (override_settings in tests will work here)
    mapping = getattr(settings, "USERS_ROLE_REDIRECTS", {}) or {}
    url_name = mapping.get(role)
    if url_name:
        return reverse(url_name)

    # 2) Sane defaults if the mapping is missing/incomplete
    try:
        # Use your project enum if present
        teacher_val = getattr(User.Roles, "TEACHER", "teacher")
        admin_val = getattr(User.Roles, "ADMIN", "admin")
    except Exception:
        teacher_val, admin_val = "teacher", "admin"

    if role == admin_val:
        return reverse("users:admin_home")
    if role == teacher_val:
        return reverse("users:teacher_home")

    # default (student or unknown)
    return reverse("users:student_home")


# --------------------------
# Auth: login / logout
# --------------------------
class EmailLoginView(LoginView):
    template_name = "users/registration/login.html"

    def get_success_url(self):
        return _redirect_for_role(self.request.user)


class EmailLogoutView(LogoutView):
    # render a page instead of redirecting
    next_page = None
    template_name = "users/registration/logged_out.html"


# --------------------------
# Auth: register
# --------------------------
class RegisterView(AdminRequiredMixin, CreateView):
    template_name = "users/registration/register.html"
    model = User
    form_class = RegisterForm
    success_url = reverse_lazy("users:student_home")  # fallback

    @transaction.atomic
    def form_valid(self, form):
        user = form.save(commit=False)
        user.role = form.cleaned_data.get("role", User.Roles.STUDENT)

        # require first-time set password
        user.set_unusable_password()

        # flags first
        if user.role in (User.Roles.TEACHER, User.Roles.ADMIN):
            user.is_staff = True

        # ✅ save BEFORE touching many-to-many relations
        user.save()

        # add group only after save
        if user.role == User.Roles.TEACHER:
            from django.contrib.auth.models import Group

            teacher_group, _ = Group.objects.get_or_create(name="Teacher Admin")
            user.groups.add(teacher_group)

        messages.success(
            self.request,
            f"User {user.email} created. An invite email will be sent automatically.",
        )

        # Redirect the creator (admin/teacher), not the new user
        return redirect(_redirect_for_role(self.request.user))


# --------------------------
# Password reset flow (centralised via PWD_RESET_TPLS)
# --------------------------
class PasswordResetStartView(PasswordResetView):
    template_name = PWD_RESET_TPLS["form"]
    email_template_name = PWD_RESET_TPLS["email_txt"]
    subject_template_name = PWD_RESET_TPLS["subject"]
    html_email_template_name = PWD_RESET_TPLS.get("email_html")
    success_url = reverse_lazy("users:password_reset_done")


class PasswordResetDoneView(PasswordResetDoneView):
    template_name = PWD_RESET_TPLS["done"]


class PasswordResetConfirmView(PasswordResetConfirmView):
    template_name = PWD_RESET_TPLS["confirm"]
    success_url = reverse_lazy("users:password_reset_complete")


class PasswordResetCompleteView(PasswordResetCompleteView):
    template_name = PWD_RESET_TPLS["complete"]


# --------------------------
# Simple role home placeholders
# --------------------------


@role_required(["student"])
def student_home(request):
    return render(request, "users/student_home.html")


@role_required(["teacher"])
def teacher_home(request):
    return render(request, "users/teacher_home.html")


@role_required(["admin"])
def admin_home(request):
    return render(request, "users/admin_home.html")
