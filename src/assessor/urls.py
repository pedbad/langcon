# src/assessor/urls.py
from django.urls import path

from . import views

app_name = "assessor"

urlpatterns = [
    path("", views.dashboard, name="teacher_home"),
    path("students/", views.students, name="students"),
    path("student/<uuid:assessment_id>/", views.student_detail, name="student_detail"),
]
