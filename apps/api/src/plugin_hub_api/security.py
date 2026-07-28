from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader
from pydantic import SecretStr

from plugin_hub_api.config import Settings

API_KEY_HEADER_NAME = "X-Plugin-Hub-Api-Key"
API_KEY_HEADER = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)
READ_METHODS = frozenset({"GET", "HEAD"})


def require_api_access(
    request: Request,
    api_key: Annotated[str | None, Security(API_KEY_HEADER)],
) -> None:
    settings = _settings(request)
    if settings.api_auth_mode == "disabled":
        return

    provided = api_key.strip() if api_key is not None else ""
    read_key = _secret_value(settings.api_read_key)
    write_key = _secret_value(settings.api_write_key)

    if request.method in READ_METHODS:
        if _matches(provided, read_key) or _matches(provided, write_key):
            return
        raise _unauthorized("api_key_required")

    if _matches(provided, write_key):
        return
    raise _unauthorized("api_write_key_required")


def _settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    return settings if isinstance(settings, Settings) else Settings()


def _secret_value(value: SecretStr | None) -> str:
    return value.get_secret_value().strip() if value is not None else ""


def _matches(provided: str, expected: str) -> bool:
    return bool(
        provided
        and expected
        and hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))
    )


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": f'ApiKey header="{API_KEY_HEADER_NAME}"'},
    )
