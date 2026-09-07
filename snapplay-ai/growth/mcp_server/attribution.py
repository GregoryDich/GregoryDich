"""The one place a published post's destination link is built.

Touch 1 of the funnel (``docs/GROWTH.md`` §4) only becomes measurable if every post sends
viewers to a URL that says which platform, which campaign and which content item it came from.
``publish_video`` tags the link per platform and stores the result on the content item, so the
landing page's analytics and the API's ``profiles`` / ``jobs`` rows can be joined back to the
post that produced them.

``utm_content`` is the content item id, which is also the key of everything the engine knows
about that clip (source, licence, angle, chosen stem), so "sign-ups per 1,000 views by angle
and source clip" is a join, not a guess.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

from .config import Platform, Settings

UTM_SOURCE: dict[str, str] = {
    "instagram": "instagram",
    "facebook": "facebook",
    "tiktok": "tiktok",
    "youtube": "youtube",
}


def utm_source_for(platform: str) -> str:
    return UTM_SOURCE.get(platform, platform)


def build_landing_url(
    settings: Settings,
    *,
    platform: Platform | str,
    content_item_id: str,
    campaign: str | None = None,
    medium: str | None = None,
) -> str:
    """The campaign-tagged landing URL for one (post, platform).

    Existing query parameters on ``GROWTH_LANDING_URL`` are preserved; the campaign parameters
    replace any of the same name. Every value is percent-encoded, so a campaign name with
    spaces, ``&`` or non-ASCII characters produces a valid URL.
    """
    parts = urlsplit(settings.growth_landing_url.strip())
    if not parts.scheme or not parts.netloc:
        raise ValueError(
            f"GROWTH_LANDING_URL must be an absolute http(s) URL, got {parts.geturl()!r}"
        )
    params = {
        "utm_source": utm_source_for(str(platform)),
        "utm_medium": medium or settings.growth_utm_medium,
        "utm_campaign": campaign or settings.growth_utm_campaign,
        "utm_content": content_item_id,
    }
    if settings.growth_referral_code:
        params["ref"] = settings.growth_referral_code
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k not in params]
    query = urlencode(kept + list(params.items()), safe="", quote_via=quote)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
