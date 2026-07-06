from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from plugin_hub_api.config import Settings
from plugin_hub_api.repositories import SqlAlchemyRepository
from plugin_hub_api.routes.collection_runs import get_repository
from plugin_hub_api.schemas import (
    JsonValue,
    Platform,
    PlatformSetting,
    PlatformSettingAuditEventsResponse,
    PlatformSettingSource,
    PlatformSettingsResponse,
    PlatformSettingUpdate,
)

router = APIRouter()

DEFAULT_UPDATED_AT = datetime(1970, 1, 1, tzinfo=UTC)
SENSITIVE_KEY_PARTS = ("token", "secret", "password", "credential", "private_key")


@router.get("/platform-settings", response_model=PlatformSettingsResponse)
def list_platform_settings(
    request: Request,
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
) -> PlatformSettingsResponse:
    stored_settings = {setting.platform: setting for setting in repository.list_platform_settings()}
    settings = [_setting_for(platform, request, stored_settings) for platform in Platform]
    return PlatformSettingsResponse(items=settings)


@router.get("/platform-settings/{platform}", response_model=PlatformSetting)
def get_platform_setting(
    platform: Platform,
    request: Request,
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
) -> PlatformSetting:
    return _setting_for(platform, request, {platform: repository.get_platform_setting(platform)})


@router.patch("/platform-settings/{platform}", response_model=PlatformSetting)
def update_platform_setting(
    platform: Platform,
    payload: PlatformSettingUpdate,
    request: Request,
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
) -> PlatformSetting:
    current = repository.get_platform_setting(platform) or _default_setting(platform, request)
    merged_config = dict(current.config)
    if payload.config is not None:
        _reject_sensitive_keys(payload.config)
        merged_config.update(payload.config)

    updated = PlatformSetting(
        platform=platform,
        enabled=current.enabled if payload.enabled is None else payload.enabled,
        config=_validated_platform_config(platform, merged_config),
        updated_at=datetime.now(tz=UTC),
        updated_by=payload.updated_by,
        source=PlatformSettingSource.STORED,
    )
    changed_fields = _changed_fields(current, updated)
    if changed_fields:
        repository.save_platform_setting(
            setting=updated,
            previous_setting=current,
            changed_fields=changed_fields,
        )
    return updated if changed_fields else current


@router.get(
    "/platform-settings/{platform}/audit-events",
    response_model=PlatformSettingAuditEventsResponse,
)
def list_platform_setting_audit_events(
    platform: Platform,
    repository: Annotated[SqlAlchemyRepository, Depends(get_repository)],
    limit: int = Query(default=20, ge=1, le=100),
) -> PlatformSettingAuditEventsResponse:
    return PlatformSettingAuditEventsResponse(
        items=repository.list_platform_setting_audit_events(platform, limit=limit)
    )


def _setting_for(
    platform: Platform,
    request: Request,
    stored_settings: Mapping[Platform, PlatformSetting | None],
) -> PlatformSetting:
    stored = stored_settings.get(platform)
    return stored if stored is not None else _default_setting(platform, request)


def _default_setting(platform: Platform, request: Request) -> PlatformSetting:
    runtime_settings = _runtime_settings(request)
    return PlatformSetting(
        platform=platform,
        enabled=platform in (Platform.AMAZON, Platform.REDDIT),
        config=_default_config(platform, runtime_settings),
        updated_at=DEFAULT_UPDATED_AT,
        updated_by="system-default",
        source=PlatformSettingSource.DEFAULT,
    )


def _runtime_settings(request: Request) -> Settings:
    settings = getattr(request.app.state, "settings", None)
    return settings if isinstance(settings, Settings) else Settings()


def _default_config(platform: Platform, settings: Settings) -> dict[str, JsonValue]:
    if platform == Platform.AMAZON:
        marketplaces: list[JsonValue] = ["US", "UK", "DE", "CA", "AU", "JP"]
        return {
            "page_limit": 3,
            "marketplaces": marketplaces,
            "notes": "",
        }
    if platform == Platform.REDDIT:
        return {
            "json_proxy_enabled": True,
            "max_comment_depth": 8,
            "notes": "",
        }
    return {
        "fixture_mode_enabled": True,
        "graph_api_version": settings.instagram_graph_api_version,
        "comment_limit": settings.instagram_graph_comment_limit,
        "notes": "",
    }


def _validated_platform_config(
    platform: Platform,
    config: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    _reject_sensitive_keys(config)
    if platform == Platform.AMAZON:
        _reject_unknown_keys(config, {"page_limit", "marketplaces", "notes"})
        return {
            "page_limit": _integer_range(config, "page_limit", minimum=1, maximum=20),
            "marketplaces": _marketplaces(config),
            "notes": _short_text(config, "notes"),
        }
    if platform == Platform.REDDIT:
        _reject_unknown_keys(config, {"json_proxy_enabled", "max_comment_depth", "notes"})
        return {
            "json_proxy_enabled": _boolean(config, "json_proxy_enabled"),
            "max_comment_depth": _integer_range(
                config,
                "max_comment_depth",
                minimum=0,
                maximum=10,
            ),
            "notes": _short_text(config, "notes"),
        }
    _reject_unknown_keys(
        config,
        {"fixture_mode_enabled", "graph_api_version", "comment_limit", "notes"},
    )
    return {
        "fixture_mode_enabled": _boolean(config, "fixture_mode_enabled"),
        "graph_api_version": _graph_api_version(config),
        "comment_limit": _integer_range(config, "comment_limit", minimum=1, maximum=100),
        "notes": _short_text(config, "notes"),
    }


def _integer_range(
    config: dict[str, JsonValue],
    key: str,
    *,
    minimum: int,
    maximum: int,
) -> int:
    value = config.get(key)
    if type(value) is not int or value < minimum or value > maximum:
        raise HTTPException(status_code=422, detail=f"{key}_out_of_range")
    return value


def _boolean(config: dict[str, JsonValue], key: str) -> bool:
    value = config.get(key)
    if type(value) is not bool:
        raise HTTPException(status_code=422, detail=f"{key}_boolean_required")
    return value


def _short_text(config: dict[str, JsonValue], key: str) -> str:
    value = config.get(key, "")
    if not isinstance(value, str) or len(value) > 240:
        raise HTTPException(status_code=422, detail=f"{key}_short_text_required")
    return value


def _marketplaces(config: dict[str, JsonValue]) -> list[JsonValue]:
    value = config.get("marketplaces")
    if not isinstance(value, list) or len(value) == 0 or len(value) > 12:
        raise HTTPException(status_code=422, detail="marketplaces_string_list_required")

    marketplaces: list[JsonValue] = []
    for item in value:
        if not isinstance(item, str) or not 2 <= len(item.strip()) <= 4:
            raise HTTPException(status_code=422, detail="marketplaces_string_list_required")
        marketplaces.append(item.strip().upper())
    return marketplaces


def _graph_api_version(config: dict[str, JsonValue]) -> str:
    value = config.get("graph_api_version")
    if not isinstance(value, str) or not value.startswith("v") or len(value) > 12:
        raise HTTPException(status_code=422, detail="graph_api_version_required")
    return value


def _reject_sensitive_keys(config: dict[str, JsonValue]) -> None:
    for key, value in config.items():
        lowered_key = key.lower()
        if any(part in lowered_key for part in SENSITIVE_KEY_PARTS):
            raise HTTPException(status_code=422, detail="sensitive_config_key_not_allowed")
        if isinstance(value, dict):
            _reject_sensitive_keys(value)


def _reject_unknown_keys(config: dict[str, JsonValue], allowed_keys: set[str]) -> None:
    unknown_keys = sorted(set(config.keys()) - allowed_keys)
    if unknown_keys:
        raise HTTPException(status_code=422, detail=f"unknown_config_key:{unknown_keys[0]}")


def _changed_fields(previous: PlatformSetting, updated: PlatformSetting) -> list[str]:
    fields: list[str] = []
    if previous.enabled != updated.enabled:
        fields.append("enabled")

    keys = sorted(set(previous.config.keys()) | set(updated.config.keys()))
    for key in keys:
        if previous.config.get(key) != updated.config.get(key):
            fields.append(f"config.{key}")
    return fields
