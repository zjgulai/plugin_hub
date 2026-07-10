from __future__ import annotations

import argparse
import json

from plugin_hub_api.config import Settings
from plugin_hub_api.db import build_engine
from plugin_hub_api.migrations import (
    applied_migration_versions,
    apply_pending_migrations,
    rollback_latest_migration,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage explicit Plugin Hub schema migrations.")
    parser.add_argument("action", choices=("status", "up", "down"))
    parser.add_argument("--database-url")
    args = parser.parse_args()

    settings = Settings()
    engine = build_engine(
        args.database_url or settings.database_url,
        sqlite_busy_timeout_ms=settings.sqlite_busy_timeout_ms,
        sqlite_wal_enabled=settings.sqlite_wal_enabled,
    )
    try:
        if args.action == "up":
            changed = apply_pending_migrations(engine)
        elif args.action == "down":
            rolled_back = rollback_latest_migration(engine)
            changed = [rolled_back] if rolled_back is not None else []
        else:
            changed = []
        print(
            json.dumps(
                {
                    "action": args.action,
                    "applied_versions": applied_migration_versions(engine),
                    "changed_versions": changed,
                    "status": "ok",
                },
                sort_keys=True,
            )
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
