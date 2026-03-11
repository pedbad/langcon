# src/core/views.py
from django.shortcuts import render


def landing_page(request):
    return render(request, "core/pages/index.html")


def about_page(request):
    return render(request, "core/pages/about.html")
