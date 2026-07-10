from __future__ import annotations

from urllib.parse import urlparse

REDDIT_SOURCE_HOSTS = frozenset(
    {
        "reddit.com",
        "www.reddit.com",
        "old.reddit.com",
        "new.reddit.com",
        "np.reddit.com",
    }
)
REDDIT_NETWORK_HOSTS = REDDIT_SOURCE_HOSTS | {"oauth.reddit.com"}
INSTAGRAM_SOURCE_HOSTS = frozenset({"instagram.com", "www.instagram.com"})
AMAZON_MARKETPLACE_SUFFIXES = frozenset(
    {
        "ae",
        "ca",
        "cn",
        "co.jp",
        "co.uk",
        "com",
        "com.au",
        "com.be",
        "com.br",
        "com.mx",
        "com.tr",
        "de",
        "eg",
        "es",
        "fr",
        "in",
        "it",
        "nl",
        "pl",
        "sa",
        "se",
        "sg",
    }
)
AMAZON_SOURCE_HOSTS = frozenset(
    host
    for suffix in AMAZON_MARKETPLACE_SUFFIXES
    for host in (f"amazon.{suffix}", f"www.amazon.{suffix}")
)


def validate_platform_source_url(platform: str, source_url: str) -> None:
    if platform == "reddit":
        validate_reddit_source_url(source_url)
        return
    if platform == "amazon":
        _validate_https_target(source_url, AMAZON_SOURCE_HOSTS, "amazon_source_url_not_allowed")
        return
    if platform == "instagram":
        _validate_https_target(
            source_url,
            INSTAGRAM_SOURCE_HOSTS,
            "instagram_source_url_not_allowed",
        )


def validate_reddit_source_url(source_url: str) -> None:
    _validate_https_target(source_url, REDDIT_SOURCE_HOSTS, "reddit_source_url_not_allowed")


def validate_reddit_network_url(source_url: str) -> None:
    _validate_https_target(source_url, REDDIT_NETWORK_HOSTS, "reddit_network_url_not_allowed")


def _validate_https_target(source_url: str, allowed_hosts: frozenset[str], error: str) -> None:
    parsed = urlparse(source_url)
    host = parsed.hostname.lower() if parsed.hostname is not None else ""
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError(error) from exc

    if (
        parsed.scheme.lower() != "https"
        or host not in allowed_hosts
        or parsed.username is not None
        or parsed.password is not None
        or port not in (None, 443)
    ):
        raise ValueError(error)
