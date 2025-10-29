from django import template

register = template.Library()

_DEFAULTS = {
    "facebook": {
        "href": "https://www.facebook.com/uclangcen/",
        "label": "Facebook",
    },
    "x": {
        "href": "https://x.com/uclangcen",
        "label": "X (Twitter)",
    },
    "youtube": {
        "href": "https://www.youtube.com/cambridgeuniversity",
        "label": "YouTube",
    },
    "linkedin": {
        "href": "https://www.linkedin.com/company/university-of-cambridge-language-centre/posts/?feedView=all",
        "label": "LinkedIn",
    },
    "instagram": {
        "href": "https://www.instagram.com/cambridgeuniversity/",
        "label": "Instagram",
    },
}


@register.inclusion_tag("core/partials/social_list.html")
def social_list(networks="facebook,x,youtube,linkedin,instagram", size="size-6"):
    """
    Render a compact list of social links.
    Usage: {% load social %} {% social_list "facebook,x,youtube" %}
    """
    names = [n.strip() for n in networks.split(",") if n.strip()]
    items = []
    for n in names:
        meta = _DEFAULTS.get(n)
        if not meta:
            continue
        items.append({"name": n, "href": meta["href"], "label": meta["label"]})
    return {"items": items, "size": size}
