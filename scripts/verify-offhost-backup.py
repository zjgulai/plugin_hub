#!/usr/bin/env python3

import argparse
import hashlib
import json
import sqlite3
import sys
from pathlib import Path


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RuntimeError(code)


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def validated_table_counts(value: object):
    require(isinstance(value, dict), "manifest_table_counts_invalid")
    counts = {}
    for table, count in value.items():
        require(isinstance(table, str) and bool(table), "manifest_table_name_invalid")
        require(
            isinstance(count, int) and not isinstance(count, bool) and count >= 0,
            f"manifest_table_count_invalid:{table}",
        )
        counts[table] = count
    return counts


def verify_backup(database_path: Path, manifest_path: Path, context: str) -> None:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(database_path.read_bytes()).hexdigest()
    expected_counts = validated_table_counts(manifest.get("table_counts"))
    connection = sqlite3.connect(
        f"{database_path.resolve().as_uri()}?mode=ro&immutable=1",
        uri=True,
    )
    try:
        connection.execute("PRAGMA query_only=ON")
        quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
        foreign_key_issues = len(
            connection.execute("PRAGMA foreign_key_check").fetchall()
        )
        actual_counts = {
            table: connection.execute(
                f"SELECT COUNT(*) FROM {quote_identifier(table)}"
            ).fetchone()[0]
            for table in expected_counts
        }
    finally:
        connection.close()

    require(
        manifest["backup_file"] == database_path.name, "manifest_backup_file_mismatch"
    )
    require(manifest["sha256"] == digest, "manifest_sha256_mismatch")
    require(
        manifest["bytes"] == database_path.stat().st_size, "manifest_bytes_mismatch"
    )
    require(manifest["quick_check_ok"] is True, "manifest_quick_check_not_ok")
    require(manifest["foreign_key_issues"] == 0, "manifest_foreign_key_issues")
    require(
        quick_check == "ok",
        "restored_database_quick_check_failed"
        if context == "restore"
        else "remote_database_quick_check_failed",
    )
    require(
        foreign_key_issues == 0,
        "restored_database_foreign_key_issues"
        if context == "restore"
        else "remote_database_foreign_key_issues",
    )
    require(expected_counts == actual_counts, "manifest_table_counts_mismatch")

    if context == "restore":
        print(
            "offhost_restore_verification=pass "
            f"file={database_path.name} "
            f"counts={actual_counts.get('collection_runs', 'missing')}/"
            f"{actual_counts.get('raw_source_items', 'missing')}/"
            f"{actual_counts.get('canonical_voc_units', 'missing')} "
            "quick_check=ok foreign_key_issues=0"
        )
    else:
        print(
            f"remote_backup_verification=pass file={database_path.name}",
            file=sys.stderr,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify a Plugin Hub off-host backup")
    parser.add_argument("--context", choices=("restore", "remote"), required=True)
    parser.add_argument("database", type=Path)
    parser.add_argument("manifest", type=Path)
    arguments = parser.parse_args()
    verify_backup(arguments.database, arguments.manifest, arguments.context)


if __name__ == "__main__":
    main()
