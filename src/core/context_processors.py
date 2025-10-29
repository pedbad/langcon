from django.conf import settings


def site_meta(_request):
    return {
        "SITE_ORIGIN": getattr(settings, "SITE_ORIGIN", ""),
        "SITE_NAME": getattr(settings, "SITE_NAME", "LangCen Base"),
    }
