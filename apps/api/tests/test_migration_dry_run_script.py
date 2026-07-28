from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest
from fastapi.testclient import TestClient

from plugin_hub_api.main import create_app
from plugin_hub_api.migrations import (
    ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION_VERSION,
    apply_pending_migrations,
)
from plugin_hub_api.payload_hashes import fnv1a64_payload_hash
from plugin_hub_api.schemas import JsonValue

REPOSITORY_ROOT = Path(__file__).parents[3]
SCRIPT_PATH = REPOSITORY_ROOT / "scripts" / "dry-run-insight-snapshot-migration.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("snapshot_migration_dry_run", SCRIPT_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("snapshot_migration_dry_run_import_failed")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    "database_path",
    [
        Path("/opt/plugin-hub/data/plugin_hub.db"),
        Path("/opt/plugin-hub/data/copies/plugin_hub.db"),
        Path("/data/plugin_hub.db"),
        Path("/data/copies/plugin_hub.db"),
    ],
)
def test_dry_run_refuses_host_and_container_live_database_roots(
    database_path: Path,
) -> None:
    script = _load_script()

    with pytest.raises(SystemExit, match="live_production_database_refused"):
        script.refuse_live_database_path(database_path)


def test_dry_run_allows_database_copy_outside_live_roots(tmp_path: Path) -> None:
    script = _load_script()

    script.refuse_live_database_path(tmp_path / "plugin_hub-copy.db")


def test_dry_run_acceptance_gate_fails_closed_under_python_optimization() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-O",
            "-c",
            (
                "from runpy import run_path; "
                f"module = run_path({str(SCRIPT_PATH)!r}); "
                "module['require'](False, 'optimized_gate_probe')"
            ),
        ],
        cwd=REPOSITORY_ROOT / "apps" / "api",
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "optimized_gate_probe" in result.stderr


def test_dry_run_upgrades_0001_copy_with_existing_snapshots(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database_path = tmp_path / "plugin_hub-copy.db"
    app = create_app(database_url=f"sqlite+pysqlite:///{database_path}")
    apply_pending_migrations(app.state.engine)
    with TestClient(app) as client:
        source_inputs = (
            (
                "amazon",
                "https://www.amazon.com/product-reviews/B000000001",
                "amazon_review",
                "review-existing",
                {
                    "review_id": "review-existing",
                    "rating": 2,
                    "body": "Existing Amazon snapshot evidence broke quickly.",
                    "asin": "B000000001",
                },
            ),
            (
                "reddit",
                "https://www.reddit.com/r/test/comments/thread/existing/",
                "reddit_thread",
                "t3_thread",
                {
                    "name": "t3_thread",
                    "id": "thread",
                    "title": "Existing Reddit snapshot evidence",
                    "selftext": "The product stopped after one week.",
                },
            ),
        )
        for platform, source_url, source_kind, source_object_id, raw in source_inputs:
            raw_payload = cast(dict[str, JsonValue], dict(raw))
            collection = client.post(
                "/api/collection-runs",
                json={
                    "run": {
                        "platform": platform,
                        "source_url": source_url,
                        "capture_method": "browser_extension",
                        "coverage_scope": {"fixture": True},
                        "stop_reason": "fixture_complete",
                        "coverage_confidence": 1.0,
                    },
                    "raw_items": [
                        {
                            "platform": platform,
                            "source_kind": source_kind,
                            "source_object_id": source_object_id,
                            "raw_schema_version": "fixture-v1",
                            "parser_version": "fixture-v1",
                            "raw_payload": raw_payload,
                            "raw_payload_hash": fnv1a64_payload_hash(raw_payload),
                            "captured_at": "2026-07-28T00:00:00+00:00",
                        }
                    ],
                },
            )
            assert collection.status_code == 201
        for platform in ("amazon", "reddit"):
            response = client.post(
                "/api/insights/snapshots",
                json={"platform": platform, "language": "zh-CN"},
            )
            assert response.status_code == 201
            assert response.json()["replayed"] is False
    app.state.engine.dispose()

    connection = sqlite3.connect(database_path)
    try:
        connection.execute("DROP TRIGGER analysis_artifacts_no_replace")
        connection.execute("DROP TRIGGER analysis_runs_no_replace")
        connection.execute(
            "DELETE FROM schema_migrations WHERE version = ?",
            (ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION_VERSION,),
        )
        connection.commit()
    finally:
        connection.close()

    script = _load_script()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT_PATH),
            "--database-path",
            str(database_path),
            "--copied-database",
        ],
    )

    script.main()

    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "pass"
    assert result["applied_now"] == [ANALYSIS_SNAPSHOT_INSERT_GUARDS_MIGRATION_VERSION]
    assert result["baseline_snapshot_run_count"] == 2
    assert result["snapshot_run_count"] == 2
    assert result["migration_checksum_verified"] is True
    assert result["insert_guard_triggers"] == [
        "analysis_artifacts_no_replace",
        "analysis_runs_no_replace",
    ]
    assert result["run_replace_guard_enforced"] is True
    assert result["artifact_replace_guard_enforced"] is True
    assert all(
        snapshot["initially_replayed"] is True
        for snapshot in result["snapshot_runs"].values()
    )


@pytest.mark.parametrize(
    "trigger_name",
    ["analysis_runs_no_replace", "analysis_artifacts_no_replace"],
)
def test_dry_run_rejects_missing_insert_guard_with_applied_migration_row(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    trigger_name: str,
) -> None:
    database_path = tmp_path / f"{trigger_name}.db"
    app = create_app(database_url=f"sqlite+pysqlite:///{database_path}")
    apply_pending_migrations(app.state.engine)
    with app.state.engine.begin() as connection:
        connection.exec_driver_sql(f'DROP TRIGGER "{trigger_name}"')
    app.state.engine.dispose()

    script = _load_script()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT_PATH),
            "--database-path",
            str(database_path),
            "--copied-database",
        ],
    )

    with pytest.raises(
        RuntimeError,
        match="analysis_snapshot_insert_guard_triggers_missing",
    ):
        script.main()
