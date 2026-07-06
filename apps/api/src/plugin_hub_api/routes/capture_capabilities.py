from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request

from plugin_hub_api.schemas import Platform, StrictBaseModel

router = APIRouter()

CaptureMode = Literal["extension", "server", "fixture"]
CaptureStatus = Literal[
    "ready",
    "authorization_required",
    "fixture_only",
    "credential_missing",
    "live_read_blocked",
    "task_authorization_required",
]


class CaptureCapability(StrictBaseModel):
    platform: Platform
    capture_method: str
    mode: CaptureMode
    status: CaptureStatus
    configured: bool
    requires_authorization: bool
    live_read_enabled: bool
    live_write_enabled: bool
    writes_canonical_voc: bool
    required_context_keys: list[str]
    evidence_grade: str
    next_required_action: str
    side_effect_boundary: str
    notes: str


class CaptureCapabilitiesResponse(StrictBaseModel):
    items: list[CaptureCapability]


@router.get("/capture-capabilities", response_model=CaptureCapabilitiesResponse)
def list_capture_capabilities(request: Request) -> CaptureCapabilitiesResponse:
    instagram_graph_configured = callable(
        getattr(request.app.state, "instagram_graph_comments_fetcher", None)
    )
    instagram_graph_live_read_enabled = bool(
        getattr(request.app.state, "instagram_graph_live_read_enabled", False)
    )

    return CaptureCapabilitiesResponse(
        items=[
            CaptureCapability(
                platform=Platform.AMAZON,
                capture_method="extension_dom_next_link_walk",
                mode="extension",
                status="ready",
                configured=True,
                requires_authorization=False,
                live_read_enabled=True,
                live_write_enabled=False,
                writes_canonical_voc=True,
                required_context_keys=[],
                evidence_grade="L1-public-or-runtime",
                next_required_action="run_extension_capture_with_browser_page_evidence",
                side_effect_boundary="capability_read_only_no_capture_started",
                notes=(
                    "Chrome extension package captures Amazon review pages and uploads raw "
                    "evidence to the shared backend."
                ),
            ),
            CaptureCapability(
                platform=Platform.REDDIT,
                capture_method="server_reddit_json_proxy",
                mode="server",
                status="ready",
                configured=True,
                requires_authorization=False,
                live_read_enabled=True,
                live_write_enabled=False,
                writes_canonical_voc=True,
                required_context_keys=["source_url"],
                evidence_grade="L1-public-or-runtime",
                next_required_action="run_server_reddit_capture_with_source_url",
                side_effect_boundary="capability_read_only_no_capture_started",
                notes=(
                    "Server-side Reddit capture derives the .json endpoint from a thread URL "
                    "and parses public JSON when reachable."
                ),
            ),
            CaptureCapability(
                platform=Platform.INSTAGRAM,
                capture_method="server_instagram_fixture_payload",
                mode="fixture",
                status="fixture_only",
                configured=True,
                requires_authorization=False,
                live_read_enabled=False,
                live_write_enabled=False,
                writes_canonical_voc=True,
                required_context_keys=["fixture_payload"],
                evidence_grade="L2-fixture-or-dry-run",
                next_required_action="use_fixture_only_for_parser_and_contract_validation",
                side_effect_boundary="fixture_only_no_instagram_live_read",
                notes=(
                    "Fixture capture is local-testable and is not evidence of authorized "
                    "Instagram live access."
                ),
            ),
            CaptureCapability(
                platform=Platform.INSTAGRAM,
                capture_method="server_instagram_graph_comments",
                mode="server",
                status=_instagram_graph_status(
                    configured=instagram_graph_configured,
                    live_read_enabled=instagram_graph_live_read_enabled,
                ),
                configured=instagram_graph_configured,
                requires_authorization=True,
                live_read_enabled=(
                    instagram_graph_configured and instagram_graph_live_read_enabled
                ),
                live_write_enabled=False,
                writes_canonical_voc=True,
                required_context_keys=[
                    "media_id",
                    "authorization_scope",
                    "authorized_by",
                    "authorized_at",
                    "environment",
                    "production_write",
                ],
                evidence_grade="L1-public-or-runtime",
                next_required_action=_instagram_graph_next_required_action(
                    configured=instagram_graph_configured,
                    live_read_enabled=instagram_graph_live_read_enabled,
                ),
                side_effect_boundary="capability_read_only_no_meta_graph_call_no_production_write",
                notes=(
                    "Instagram Graph comment capture requires a backend-only Meta access token "
                    "plus live-read environment and task authorization gates."
                ),
            ),
        ]
    )


def _instagram_graph_status(*, configured: bool, live_read_enabled: bool) -> CaptureStatus:
    if not configured:
        return "credential_missing"
    if not live_read_enabled:
        return "live_read_blocked"
    return "task_authorization_required"


def _instagram_graph_next_required_action(
    *, configured: bool, live_read_enabled: bool
) -> str:
    if not configured:
        return "confirm_data_rights_then_configure_backend_only_meta_token"
    if not live_read_enabled:
        return "obtain_explicit_live_read_approval_then_enable_backend_switch"
    return "submit_task_authorization_context_to_preflight"
