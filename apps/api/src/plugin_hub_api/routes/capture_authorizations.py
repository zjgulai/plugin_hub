from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request
from pydantic import Field, field_validator

from plugin_hub_api.schemas import JsonValue, Platform, StrictBaseModel, ensure_json_object
from plugin_hub_api.services.instagram_graph_authorization import (
    INSTAGRAM_GRAPH_LIVE_READ_REQUIRED_CONTEXT_KEYS,
    validate_instagram_graph_live_read_context,
)

router = APIRouter()

InstagramGraphLiveReadPreflightStatus = Literal[
    "ready",
    "credential_missing",
    "live_read_blocked",
    "task_authorization_required",
]


class InstagramGraphLiveReadPreflightRequest(StrictBaseModel):
    context: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("context", mode="before")
    @classmethod
    def validate_context(cls, value: object) -> dict[str, JsonValue]:
        return ensure_json_object(value)


class InstagramGraphLiveReadPreflightResponse(StrictBaseModel):
    platform: Platform
    capture_method: str
    status: InstagramGraphLiveReadPreflightStatus
    configured: bool
    live_read_enabled: bool
    task_authorization_ready: bool
    ready_for_worker: bool
    required_context_keys: list[str]
    missing_context_keys: list[str]
    invalid_context_keys: list[str]
    blocking_code: str | None
    evidence_grade: str
    next_required_action: str
    side_effect_boundary: str
    notes: str


@router.post(
    "/capture-authorizations/instagram-graph-live-read/preflight",
    response_model=InstagramGraphLiveReadPreflightResponse,
)
def preflight_instagram_graph_live_read_authorization(
    payload: InstagramGraphLiveReadPreflightRequest,
    request: Request,
) -> InstagramGraphLiveReadPreflightResponse:
    configured = callable(getattr(request.app.state, "instagram_graph_comments_fetcher", None))
    live_read_enabled = bool(getattr(request.app.state, "instagram_graph_live_read_enabled", False))
    authorization_check = validate_instagram_graph_live_read_context(payload.context)
    status = _preflight_status(
        configured=configured,
        live_read_enabled=live_read_enabled,
        task_authorization_ready=authorization_check.ready,
    )

    return InstagramGraphLiveReadPreflightResponse(
        platform=Platform.INSTAGRAM,
        capture_method="server_instagram_graph_comments",
        status=status,
        configured=configured,
        live_read_enabled=configured and live_read_enabled,
        task_authorization_ready=authorization_check.ready,
        ready_for_worker=status == "ready",
        required_context_keys=INSTAGRAM_GRAPH_LIVE_READ_REQUIRED_CONTEXT_KEYS,
        missing_context_keys=authorization_check.missing_context_keys,
        invalid_context_keys=authorization_check.invalid_context_keys,
        blocking_code=authorization_check.blocking_code,
        evidence_grade="L2-fixture-or-dry-run",
        next_required_action=_next_required_action(status),
        side_effect_boundary="dry_preflight_only_no_meta_graph_call_no_production_write",
        notes=(
            "Preflight checks backend Graph configuration, live-read switch, and task "
            "authorization context without calling Meta Graph endpoints."
        ),
    )


def _preflight_status(
    *, configured: bool, live_read_enabled: bool, task_authorization_ready: bool
) -> InstagramGraphLiveReadPreflightStatus:
    if not configured:
        return "credential_missing"
    if not live_read_enabled:
        return "live_read_blocked"
    if not task_authorization_ready:
        return "task_authorization_required"
    return "ready"


def _next_required_action(status: InstagramGraphLiveReadPreflightStatus) -> str:
    if status == "credential_missing":
        return "confirm_data_rights_then_configure_backend_only_meta_token"
    if status == "live_read_blocked":
        return "obtain_explicit_live_read_approval_then_enable_backend_switch"
    if status == "task_authorization_required":
        return "fix_task_authorization_context_before_worker_execution"
    return "run_authorized_read_only_task_only_after_approval"
