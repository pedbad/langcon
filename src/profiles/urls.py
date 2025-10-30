# src/profiles/urls.py
from django.urls import path

from . import views

app_name = "profiles"

urlpatterns = [
    path("", views.student_profile_entry, name="profile"),
]
