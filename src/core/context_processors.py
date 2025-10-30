from django.conf import settings


def site_meta(_request):
    return {
        "SITE_ORIGIN": getattr(settings, "SITE_ORIGIN", ""),
        "SITE_NAME": getattr(settings, "SITE_NAME", "LangCon"),
        "SITE_DESCRIPTION": getattr(
            settings,
            "SITE_DESCRIPTION",
            "Graduate Applications - Language Condition",
        ),
    }
