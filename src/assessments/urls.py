from django.urls import path
from . import views

app_name = "assessments"

urlpatterns = [
    path("", views.home, name="home"), # /assessments/ → assessments:home
]
