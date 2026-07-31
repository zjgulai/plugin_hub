from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import runpy
import shutil
import sqlite3
import subprocess
import sys
import tarfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from plugin_hub_api.backup_cli import create_verified_backup, verify_sqlite_backup


def test_create_verified_backup_is_consistent_and_prunes_only_after_success(
    tmp_path: Path,
) -> None:
    source = tmp_path / "plugin_hub.db"
    destination = tmp_path / "backups"
    with sqlite3.connect(source) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE collection_runs (id TEXT PRIMARY KEY)")
        connection.executemany(
            "INSERT INTO collection_runs (id) VALUES (?)",
            [("run-1",), ("run-2",)],
        )

    started_at = datetime(2026, 7, 10, 3, 15, tzinfo=UTC)
    results = [
        create_verified_backup(
            source=source,
            destination_dir=destination,
            retention_count=2,
            now=started_at + timedelta(days=offset),
        )
        for offset in range(3)
    ]

    backups = sorted(destination.glob("plugin_hub_*.db"))
    assert backups == [results[1].backup_path, results[2].backup_path]
    verification = verify_sqlite_backup(results[2].backup_path)
    assert verification.quick_check_ok is True
    assert verification.foreign_key_issues == 0
    assert verification.table_counts == {"collection_runs": 2}
    manifest = json.loads(results[2].manifest_path.read_text())
    assert manifest["quick_check_ok"] is True
    assert manifest["foreign_key_issues"] == 0
    assert manifest["table_counts"] == {"collection_runs": 2}
    assert len(manifest["sha256"]) == 64
    assert results[0].backup_path.exists() is False
    assert results[0].manifest_path.exists() is False
    assert destination.stat().st_mode & 0o777 == 0o700
    assert (destination / ".plugin_hub_backup.lock").stat().st_mode & 0o777 == 0o600
    assert all(path.stat().st_mode & 0o777 == 0o600 for path in destination.iterdir())
    assert not any(
        path.name.endswith(("-wal", "-shm")) or ".tmp" in path.name
        for path in destination.iterdir()
    )


def test_backup_rejects_foreign_key_violations_before_publication(tmp_path: Path) -> None:
    source = tmp_path / "plugin_hub.db"
    destination = tmp_path / "backups"
    with sqlite3.connect(source) as connection:
        connection.executescript(
            """
            PRAGMA foreign_keys=OFF;
            CREATE TABLE collection_runs (id TEXT PRIMARY KEY);
            CREATE TABLE raw_source_items (
                id INTEGER PRIMARY KEY,
                collection_run_id TEXT REFERENCES collection_runs(id)
            );
            INSERT INTO raw_source_items (collection_run_id) VALUES ('missing-run');
            """
        )

    verification = verify_sqlite_backup(source)
    assert verification.quick_check_ok is True
    assert verification.foreign_key_issues == 1

    with pytest.raises(RuntimeError, match="backup_foreign_key_check_failed"):
        create_verified_backup(
            source=source,
            destination_dir=destination,
            retention_count=2,
            now=datetime(2026, 7, 10, 3, 15, tzinfo=UTC),
        )

    assert list(destination.glob("plugin_hub_*.db")) == []
    assert list(destination.glob("plugin_hub_*.manifest.json")) == []


def test_retention_does_not_count_tampered_backup_as_verified(tmp_path: Path) -> None:
    source = tmp_path / "plugin_hub.db"
    destination = tmp_path / "backups"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE raw_source_items (id INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO raw_source_items DEFAULT VALUES")

    started_at = datetime(2026, 7, 10, 3, 15, tzinfo=UTC)
    oldest = create_verified_backup(
        source=source,
        destination_dir=destination,
        retention_count=2,
        now=started_at,
    )
    tampered = create_verified_backup(
        source=source,
        destination_dir=destination,
        retention_count=2,
        now=started_at + timedelta(days=1),
    )
    with tampered.backup_path.open("ab") as file_handle:
        file_handle.write(b"tampered")

    newest = create_verified_backup(
        source=source,
        destination_dir=destination,
        retention_count=2,
        now=started_at + timedelta(days=2),
    )

    assert oldest.backup_path.exists() is True
    assert tampered.backup_path.exists() is True
    assert newest.backup_path.exists() is True

    next_backup = create_verified_backup(
        source=source,
        destination_dir=destination,
        retention_count=2,
        now=started_at + timedelta(days=3),
    )

    assert oldest.backup_path.exists() is False
    assert tampered.backup_path.exists() is True
    assert newest.backup_path.exists() is True
    assert next_backup.backup_path.exists() is True


def test_offhost_pull_reports_legacy_lock_and_ignores_unlocked_lock_file(tmp_path: Path) -> None:
    zsh = shutil.which("zsh")
    if zsh is None or not Path("/usr/bin/lockf").exists():
        pytest.skip("offhost pull locking is a macOS zsh workflow")

    script = Path(__file__).parents[3] / "scripts" / "pull-offhost-backup.zsh"
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    no_output_tool = tools_dir / "no-output"
    no_output_tool.write_text("#!/bin/sh\nexit 0\n")
    no_output_tool.chmod(0o700)
    recipient_file = tmp_path / "recipient.txt"
    recipient_file.write_text("age1testrecipient\n")
    destination_dir = tmp_path / "backups"
    destination_dir.mkdir()
    environment = {
        **os.environ,
        "PLUGIN_HUB_BACKUP_DESTINATION_DIR": str(destination_dir),
        "PLUGIN_HUB_BACKUP_RECIPIENT_FILE": str(recipient_file),
        "PLUGIN_HUB_AGE_BIN": str(no_output_tool),
        "PLUGIN_HUB_SSH_BIN": str(no_output_tool),
        "PLUGIN_HUB_SECURITY_BIN": str(no_output_tool),
    }

    lock_path = destination_dir / ".pull.lock"
    lock_path.mkdir()
    legacy_result = subprocess.run(
        [zsh, str(script)],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert legacy_result.returncode == 75
    assert "offhost_backup_error=legacy_lock_directory_detected" in legacy_result.stderr

    lock_path.rmdir()
    lock_path.write_text("stale-content\n")
    stale_file_result = subprocess.run(
        [zsh, str(script)],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert stale_file_result.returncode == 1
    assert "offhost_backup_error=invalid_remote_manifest_name" in stale_file_result.stderr
    assert "already_running" not in stale_file_result.stderr


def test_offhost_pull_rejects_missing_python_before_remote_access(tmp_path: Path) -> None:
    zsh = shutil.which("zsh")
    if zsh is None:
        pytest.skip("offhost pull is a macOS zsh workflow")

    script = Path(__file__).parents[3] / "scripts" / "pull-offhost-backup.zsh"
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    no_output_tool = tools_dir / "no-output"
    no_output_tool.write_text("#!/bin/sh\nexit 0\n")
    no_output_tool.chmod(0o700)
    ssh_probe = tmp_path / "ssh-invoked"
    ssh_tool = tools_dir / "ssh-probe"
    ssh_tool.write_text('#!/bin/sh\n: > "$PLUGIN_HUB_SSH_PROBE"\nexit 0\n')
    ssh_tool.chmod(0o700)
    recipient_file = tmp_path / "recipient.txt"
    recipient_file.write_text("age1testrecipient\n")

    result = subprocess.run(
        [zsh, str(script)],
        env={
            **os.environ,
            "PLUGIN_HUB_BACKUP_DESTINATION_DIR": str(tmp_path / "backups"),
            "PLUGIN_HUB_BACKUP_RECIPIENT_FILE": str(recipient_file),
            "PLUGIN_HUB_AGE_BIN": str(no_output_tool),
            "PLUGIN_HUB_SSH_BIN": str(ssh_tool),
            "PLUGIN_HUB_SECURITY_BIN": str(no_output_tool),
            "PLUGIN_HUB_PYTHON_BIN": str(tools_dir / "missing-python"),
            "PLUGIN_HUB_SSH_PROBE": str(ssh_probe),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "offhost_backup_error=required_tool_missing" in result.stderr
    assert ssh_probe.exists() is False


def test_offhost_pull_rejects_missing_validator_before_remote_access(tmp_path: Path) -> None:
    zsh = shutil.which("zsh")
    if zsh is None:
        pytest.skip("offhost pull is a macOS zsh workflow")

    script = Path(__file__).parents[3] / "scripts" / "pull-offhost-backup.zsh"
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    no_output_tool = tools_dir / "no-output"
    no_output_tool.write_text("#!/bin/sh\nexit 0\n")
    no_output_tool.chmod(0o700)
    ssh_probe = tmp_path / "ssh-invoked"
    ssh_tool = tools_dir / "ssh-probe"
    ssh_tool.write_text('#!/bin/sh\n: > "$PLUGIN_HUB_SSH_PROBE"\nexit 0\n')
    ssh_tool.chmod(0o700)
    recipient_file = tmp_path / "recipient.txt"
    recipient_file.write_text("age1testrecipient\n")

    result = subprocess.run(
        [zsh, str(script)],
        env={
            **os.environ,
            "PLUGIN_HUB_BACKUP_DESTINATION_DIR": str(tmp_path / "backups"),
            "PLUGIN_HUB_BACKUP_RECIPIENT_FILE": str(recipient_file),
            "PLUGIN_HUB_AGE_BIN": str(no_output_tool),
            "PLUGIN_HUB_SSH_BIN": str(ssh_tool),
            "PLUGIN_HUB_SECURITY_BIN": str(no_output_tool),
            "PLUGIN_HUB_BACKUP_VALIDATOR_SCRIPT": str(tools_dir / "missing-validator.py"),
            "PLUGIN_HUB_SSH_PROBE": str(ssh_probe),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "offhost_backup_error=validator_script_missing" in result.stderr
    assert ssh_probe.exists() is False


def test_offhost_pull_uses_shared_validator_for_local_and_remote_paths() -> None:
    script = Path(__file__).parents[3] / "scripts" / "pull-offhost-backup.zsh"
    script_text = script.read_text()

    assert "verify-offhost-backup.py" in script_text
    assert script_text.count("--context restore") == 1
    assert script_text.count("--context remote") == 1
    assert "def validated_table_counts" not in script_text


def test_offhost_remote_flow_executes_shared_validator_before_tar(tmp_path: Path) -> None:
    bash = shutil.which("bash")
    if bash is None:
        pytest.skip("remote backup wrapper requires bash")

    repository_root = Path(__file__).parents[3]
    script = repository_root / "scripts" / "pull-offhost-backup.zsh"
    validator = repository_root / "scripts" / "verify-offhost-backup.py"
    remote_section = script.read_text().split("<<'REMOTE'", maxsplit=2)[2]
    remote_code = remote_section.split("\n", maxsplit=1)[1].split("\nREMOTE", maxsplit=1)[0]
    database = tmp_path / "plugin_hub_20260730T000002Z.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE collection_runs (id INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO collection_runs DEFAULT VALUES")
    manifest = tmp_path / "plugin_hub_20260730T000002Z.manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "backup_file": database.name,
                "bytes": database.stat().st_size,
                "foreign_key_issues": 0,
                "quick_check_ok": True,
                "sha256": hashlib.sha256(database.read_bytes()).hexdigest(),
                "table_counts": {"collection_runs": 1},
            }
        )
    )
    tools_dir = tmp_path / "tools"
    tools_dir.mkdir()
    sudo_tool = tools_dir / "sudo"
    sudo_tool.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = "-n" ]; then shift; fi\n'
        'if [ "$1" = "python3" ]; then shift; exec "$TEST_PYTHON" "$@"; fi\n'
        'exec "$@"\n'
    )
    sudo_tool.chmod(0o700)
    validator_payload = base64.b64encode(validator.read_bytes()).decode()

    result = subprocess.run(
        [
            bash,
            "-s",
            "--",
            str(tmp_path),
            database.name,
            manifest.name,
            validator_payload,
        ],
        input=remote_code.encode(),
        env={
            **os.environ,
            "PATH": f"{tools_dir}:{os.environ['PATH']}",
            "TEST_PYTHON": sys.executable,
        },
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr.decode()
    assert "remote_backup_verification=pass" in result.stderr.decode()
    with tarfile.open(fileobj=io.BytesIO(result.stdout), mode="r:") as archive:
        assert {database.name, manifest.name} <= set(archive.getnames())


def test_offhost_restore_verification_checks_every_manifest_table(tmp_path: Path) -> None:
    validator = Path(__file__).parents[3] / "scripts" / "verify-offhost-backup.py"
    database = tmp_path / "plugin_hub_20260730T000000Z.db"
    with sqlite3.connect(database) as connection:
        connection.executescript(
            """
            CREATE TABLE collection_runs (id INTEGER PRIMARY KEY);
            CREATE TABLE raw_source_items (id INTEGER PRIMARY KEY);
            CREATE TABLE canonical_voc_units (id INTEGER PRIMARY KEY);
            CREATE TABLE analysis_snapshots (id INTEGER PRIMARY KEY);
            INSERT INTO analysis_snapshots DEFAULT VALUES;
            """
        )
    manifest = tmp_path / "plugin_hub_20260730T000000Z.manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "backup_file": database.name,
                "bytes": database.stat().st_size,
                "foreign_key_issues": 0,
                "quick_check_ok": True,
                "sha256": hashlib.sha256(database.read_bytes()).hexdigest(),
                "table_counts": {
                    "analysis_snapshots": 0,
                    "canonical_voc_units": 0,
                    "collection_runs": 0,
                    "raw_source_items": 0,
                },
            }
        )
    )

    result = subprocess.run(
        [
            sys.executable,
            str(validator),
            "--context",
            "restore",
            str(database),
            str(manifest),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert "manifest_table_counts_mismatch" in result.stderr
    assert "Traceback" not in result.stderr


def test_offhost_verification_hashes_database_without_path_read_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    validator = Path(__file__).parents[3] / "scripts" / "verify-offhost-backup.py"
    database = tmp_path / "plugin_hub_20260730T000003Z.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE collection_runs (id INTEGER PRIMARY KEY)")
        connection.execute("INSERT INTO collection_runs DEFAULT VALUES")
    manifest = tmp_path / "plugin_hub_20260730T000003Z.manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "backup_file": database.name,
                "bytes": database.stat().st_size,
                "foreign_key_issues": 0,
                "quick_check_ok": True,
                "sha256": hashlib.sha256(database.read_bytes()).hexdigest(),
                "table_counts": {"collection_runs": 1},
            }
        )
    )
    verify_backup = runpy.run_path(str(validator))["verify_backup"]

    def reject_read_bytes(_path: Path) -> bytes:
        raise AssertionError("backup hashing must stream bounded chunks")

    monkeypatch.setattr(Path, "read_bytes", reject_read_bytes)

    verify_backup(database, manifest, "restore")


@pytest.mark.parametrize(
    ("manifest_payload", "expected_error"),
    [
        ("{", "Expecting property name enclosed in double quotes"),
        (
            json.dumps(
                {
                    "bytes": 0,
                    "foreign_key_issues": 0,
                    "quick_check_ok": True,
                    "sha256": hashlib.sha256(b"").hexdigest(),
                    "table_counts": {},
                }
            ),
            "'backup_file'",
        ),
        (
            json.dumps(
                {
                    "backup_file": "backup.db",
                    "bytes": 0,
                    "foreign_key_issues": 0,
                    "quick_check_ok": True,
                    "sha256": hashlib.sha256(b"").hexdigest(),
                    "table_counts": {"missing_table": 0},
                }
            ),
            "no such table: missing_table",
        ),
    ],
)
def test_offhost_verification_reports_clean_single_line_errors(
    tmp_path: Path, manifest_payload: str, expected_error: str
) -> None:
    validator = Path(__file__).parents[3] / "scripts" / "verify-offhost-backup.py"
    database = tmp_path / "backup.db"
    database.touch()
    manifest = tmp_path / "backup.manifest.json"
    manifest.write_text(manifest_payload)

    result = subprocess.run(
        [
            sys.executable,
            str(validator),
            "--context",
            "restore",
            str(database),
            str(manifest),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert result.stdout == ""
    assert result.stderr.startswith("offhost_backup_verification_error=")
    assert result.stderr.count("\n") == 1
    assert expected_error in result.stderr
    assert "Traceback" not in result.stderr


def test_offhost_restore_verification_quotes_manifest_table_names(tmp_path: Path) -> None:
    validator = Path(__file__).parents[3] / "scripts" / "verify-offhost-backup.py"
    database = tmp_path / "plugin_hub_20260730T000001Z.db"
    with sqlite3.connect(database) as connection:
        connection.execute('CREATE TABLE "analysis""snapshots" (id INTEGER PRIMARY KEY)')
        connection.execute('INSERT INTO "analysis""snapshots" DEFAULT VALUES')
    manifest = tmp_path / "plugin_hub_20260730T000001Z.manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "backup_file": database.name,
                "bytes": database.stat().st_size,
                "foreign_key_issues": 0,
                "quick_check_ok": True,
                "sha256": hashlib.sha256(database.read_bytes()).hexdigest(),
                "table_counts": {'analysis"snapshots': 1},
            }
        )
    )

    for context, expected_output in (
        ("restore", "offhost_restore_verification=pass"),
        ("remote", "remote_backup_verification=pass"),
    ):
        result = subprocess.run(
            [
                sys.executable,
                str(validator),
                "--context",
                context,
                str(database),
                str(manifest),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        assert expected_output in result.stdout + result.stderr


def test_offhost_publication_commits_metadata_before_archive() -> None:
    script = Path(__file__).parents[3] / "scripts" / "pull-offhost-backup.zsh"
    script_text = script.read_text()

    metadata_move = script_text.index('mv "$temporary_metadata" "$final_metadata"')
    metadata_release = script_text.index('temporary_metadata=""', metadata_move)
    archive_move = script_text.index('mv "$temporary_archive" "$final_archive"')
    archive_release = script_text.index('temporary_archive=""', archive_move)

    assert metadata_move < metadata_release < archive_move < archive_release


def test_offhost_retention_counts_only_verified_archives(tmp_path: Path) -> None:
    script = Path(__file__).parents[3] / "scripts" / "pull-offhost-backup.zsh"
    script_text = script.read_text()
    retention_code = script_text.split("<<'PY_RETENTION'\n", maxsplit=1)[1].split(
        "\nPY_RETENTION", maxsplit=1
    )[0]
    destination = tmp_path / "offhost"
    destination.mkdir()

    def write_archive(timestamp: str, content: bytes, *, valid_metadata: bool = True) -> str:
        archive_name = f"plugin_hub_{timestamp}.tar.age"
        archive = destination / archive_name
        archive.write_bytes(content)
        if valid_metadata:
            metadata = destination / f"plugin_hub_{timestamp}.offhost.json"
            metadata.write_text(
                json.dumps(
                    {
                        "archive_file": archive_name,
                        "encrypted_bytes": len(content),
                        "encrypted_sha256": hashlib.sha256(content).hexdigest(),
                        "verification": "decrypt_manifest_hash_quick_check_counts_fk",
                    }
                )
            )
        return archive_name

    missing_metadata = write_archive("20260714T000000Z", b"unverified", valid_metadata=False)
    newest = write_archive("20260713T000000Z", b"verified-newest")
    middle = write_archive("20260712T000000Z", b"verified-middle")
    oldest = write_archive("20260711T000000Z", b"verified-oldest")

    result = subprocess.run(
        [sys.executable, "-", str(destination), "2"],
        input=retention_code,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.splitlines() == [oldest]
    assert missing_metadata in result.stderr
    assert newest not in result.stdout
    assert middle not in result.stdout


def test_offhost_metadata_verification_rejects_mismatched_sidecar(tmp_path: Path) -> None:
    script = Path(__file__).parents[3] / "scripts" / "pull-offhost-backup.zsh"
    script_text = script.read_text()
    verification_code = script_text.split("<<'PY_METADATA'\n", maxsplit=1)[1].split(
        "\nPY_METADATA", maxsplit=1
    )[0]
    archive = tmp_path / "plugin_hub_20260728T000000Z.tar.age"
    archive.write_bytes(b"encrypted-backup")
    archive_name = archive.name
    database_name = "plugin_hub_20260728T000000Z.db"
    remote_host = "backup-host"
    metadata = tmp_path / "plugin_hub_20260728T000000Z.offhost.json"
    payload = {
        "archive_file": archive_name,
        "encrypted_bytes": archive.stat().st_size,
        "encrypted_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "fetched_at": "2026-07-28T00:00:00Z",
        "remote_host": remote_host,
        "source_backup_file": database_name,
        "verification": "decrypt_manifest_hash_quick_check_counts_fk",
    }
    metadata.write_text(json.dumps(payload))

    valid_result = subprocess.run(
        [
            sys.executable,
            "-",
            str(archive),
            str(metadata),
            archive_name,
            database_name,
            remote_host,
        ],
        input=verification_code,
        env={**os.environ, "PYTHONOPTIMIZE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert valid_result.returncode == 0

    payload["encrypted_sha256"] = "0" * 64
    metadata.write_text(json.dumps(payload))
    mismatched_result = subprocess.run(
        [
            sys.executable,
            "-",
            str(archive),
            str(metadata),
            archive_name,
            database_name,
            remote_host,
        ],
        input=verification_code,
        env={**os.environ, "PYTHONOPTIMIZE": "1"},
        capture_output=True,
        text=True,
        check=False,
    )
    assert mismatched_result.returncode != 0
