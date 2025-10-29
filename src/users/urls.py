# src/users/urls.py
from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    # auth
    path("login/", views.EmailLoginView.as_view(), name="login"),
    path("logout/", views.EmailLogoutView.as_view(), name="logout"),
    path("register/", views.RegisterView.as_view(), name="register"),
    # dashboards / placeholders (so redirects resolve without other apps)
    path("student/", views.student_home, name="student_home"),
    path("teacher/", views.teacher_home, name="teacher_home"),
    path("admin-home/", views.admin_home, name="admin_home"),
    # password reset (Django’s built-in views, via our wrappers)
    path("password-reset/", views.PasswordResetStartView.as_view(), name="password_reset"),
    path(
        "password-reset/done/",
        views.PasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "reset/<uidb64>/<token>/",
        views.PasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "reset/done/",
        views.PasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
]
