# src/assessor/urls.py
from django.urls import path

from . import views

app_name = "assessor"

urlpatterns = [
    path("", views.dashboard, name="teacher_home"),
]
