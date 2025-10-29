# src/core/views.py
from django.contrib import messages
from django.shortcuts import render


def landing_page(request):
    return render(request, "core/pages/index.html")


def about_page(request):
    messages.info(request, "Heads up: this is an informational message.")
    messages.success(request, "Nice! Your profile was saved successfully.")
    messages.warning(request, "Careful: this action might have side effects.")
    messages.error(request, "Oops! Something went wrong while processing your request.")

    icon_list = [
        "info",
        "success",
        "warning",
        "error",
        "home",
        "admin",
        "login",
        "logout",
        "dashboard",
        "computer",
        "dark_mode",
        "light_mode",
    ]

    return render(request, "core/pages/about.html", {"icon_list": icon_list})
