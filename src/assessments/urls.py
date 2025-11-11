# src/assessments/urls.py

from django.urls import path

from . import views

app_name = "assessments"

urlpatterns = [
    path("", views.gate, name="gate"),  # ← always accessible
    path("home/", views.home, name="home"),  # ← real assessment landing
    path("test/", views.llm_test, name="test"),  # dev/test endpoint
]
