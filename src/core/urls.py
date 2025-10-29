# src/core/urls.py
from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.landing_page, name="landing"),
    path("about/", views.about_page, name="about"),
]
