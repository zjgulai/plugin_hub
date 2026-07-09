from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from plugin_hub_api.schemas import JsonValue

INSTAGRAM_GRAPH_LIVE_READ_SCOPE = "instagram_graph_live_read"
INSTAGRAM_GRAPH_LIVE_READ_ENVIRONMENTS = {"local", "staging", "production"}
INSTAGRAM_GRAPH_LIVE_READ_REQUIRED_CONTEXT_KEYS = [
    "media_id",
    "authorization_scope",
    "authorized_by",
    "authorized_at",
    "environment",
    "production_write",
]


@dataclass(frozen=True)
class InstagramGraphLiveReadAuthorizationCheck:
    ready: bool
    missing_context_keys: list[str]
    invalid_context_keys: list[str]
    blocking_code: str | None


def validate_instagram_graph_live_read_context(
    context: Mapping[str, JsonValue],
) -> InstagramGraphLiveReadAuthorizationCheck:
    missing_context_keys: list[str] = []
    invalid_context_keys: list[str] = []

    media_id = context.get("media_id")
    if not isinstance(media_id, str) or not media_id.strip():
        missing_context_keys.append("media_id")

    authorization_scope = context.get("authorization_scope")
    if authorization_scope is None:
        missing_context_keys.append("authorization_scope")
    elif authorization_scope != INSTAGRAM_GRAPH_LIVE_READ_SCOPE:
        invalid_context_keys.append("authorization_scope")

    authorized_by = context.get("authorized_by")
    if not isinstance(authorized_by, str) or not authorized_by.strip():
        missing_context_keys.append("authorized_by")

    authorized_at = context.get("authorized_at")
    if not isinstance(authorized_at, str) or not authorized_at.strip():
        missing_context_keys.append("authorized_at")

    environment = context.get("environment")
    if environment is None:
        missing_context_keys.append("environment")
    elif environment not in INSTAGRAM_GRAPH_LIVE_READ_ENVIRONMENTS:
        invalid_context_keys.append("environment")

    production_write = context.get("production_write")
    if production_write is None:
        missing_context_keys.append("production_write")
    elif production_write is not False:
        invalid_context_keys.append("production_write")

    blocking_code = _blocking_code(
        missing_context_keys=missing_context_keys,
        invalid_context_keys=invalid_context_keys,
    )
    return InstagramGraphLiveReadAuthorizationCheck(
        ready=blocking_code is None,
        missing_context_keys=missing_context_keys,
        invalid_context_keys=invalid_context_keys,
        blocking_code=blocking_code,
    )


def _blocking_code(
    *, missing_context_keys: list[str], invalid_context_keys: list[str]
) -> str | None:
    if "media_id" in missing_context_keys:
        return "instagram_graph_media_id_required"
    if "production_write" in invalid_context_keys:
        return "instagram_graph_live_read_production_write_must_be_false"
    if missing_context_keys or invalid_context_keys:
        return "instagram_graph_live_read_authorization_required"
    return None
