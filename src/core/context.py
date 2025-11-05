from django.conf import settings


def core_settings(request):
    return {
        "ENV": getattr(settings, "ENV", "dev"),
        "DEBUG_FLAG": bool(getattr(settings, "DEBUG", False)),
        "STATIC_VERSION": getattr(settings, "STATIC_VERSION", "dev-0"),
    }
