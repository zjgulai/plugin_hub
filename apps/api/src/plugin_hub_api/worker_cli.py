from __future__ import annotations

import argparse
import logging
import time
from collections.abc import Callable

from sqlalchemy.orm import Session

from plugin_hub_api.config import Settings
from plugin_hub_api.db import build_engine, init_database, make_session_factory
from plugin_hub_api.repositories import SqlAlchemyRepository
from plugin_hub_api.services.collection_task_worker import (
    CollectionTaskWorkerConfig,
    PendingCollectionTaskNotFoundError,
    run_next_collection_task,
)
from plugin_hub_api.services.reddit_capture import default_reddit_json_fetcher


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Background worker that consumes pending collection tasks."
    )
    parser.add_argument(
        "--database-url",
        default=None,
        help="Override PLUGIN_HUB_DATABASE_URL if provided.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process only one runnable task, then exit.",
    )
    parser.add_argument(
        "--max-tasks",
        type=int,
        default=0,
        help="Maximum runnable tasks to process in one run. 0 means unlimited.",
    )
    parser.add_argument(
        "--poll-interval-seconds",
        type=float,
        default=3.0,
        help="Sleep interval when no runnable task is found.",
    )
    parser.add_argument(
        "--max-attempts",
        type=int,
        default=None,
        help="Override default max retry attempts.",
    )
    parser.add_argument(
        "--retry-delay-seconds",
        type=int,
        default=None,
        help="Override retry delay used for scheduled retries.",
    )
    parser.add_argument(
        "--claim-ttl-seconds",
        type=int,
        default=None,
        help="Override claim TTL for worker locking.",
    )
    parser.add_argument(
        "--worker-id",
        default=None,
        help="Identifier included in task context for tracing.",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
    )
    return parser.parse_args()


def build_config(settings: Settings, args: argparse.Namespace) -> CollectionTaskWorkerConfig:
    return CollectionTaskWorkerConfig(
        max_attempts=(
            args.max_attempts
            if args.max_attempts is not None
            else settings.collection_task_max_attempts
        ),
        retry_delay_seconds=(
            args.retry_delay_seconds
            if args.retry_delay_seconds is not None
            else settings.collection_task_retry_delay_seconds
        ),
        claim_ttl_seconds=(
            args.claim_ttl_seconds
            if args.claim_ttl_seconds is not None
            else settings.collection_task_claim_ttl_seconds
        ),
        worker_id=args.worker_id or settings.collection_task_worker_id,
    )


def run_worker(
    *,
    session_factory: Callable[[], Session],
    config: CollectionTaskWorkerConfig,
    once: bool,
    max_tasks: int,
    poll_interval_seconds: float,
) -> int:
    processed_count = 0
    while True:
        with session_factory() as session:
            repository = SqlAlchemyRepository(session)
            try:
                result = run_next_collection_task(
                    repository=repository,
                    reddit_json_fetcher=default_reddit_json_fetcher,
                    config=config,
                )
            except PendingCollectionTaskNotFoundError:
                logging.info("No runnable task found.")
                if once:
                    return processed_count
            except Exception:
                logging.exception("Collection worker iteration failed.")
                if once:
                    return processed_count
            else:
                processed_count += 1
                logging.info(
                    "Processed collection task: %s status=%s run_id=%s raw=%s voc=%s",
                    result.task.collection_task_id,
                    result.task.status,
                    result.collection_run_id,
                    result.raw_item_count,
                    result.voc_unit_count,
                )
                if max_tasks > 0 and processed_count >= max_tasks:
                    return processed_count

        if once or (max_tasks > 0 and processed_count >= max_tasks):
            return processed_count

        if poll_interval_seconds > 0:
            time.sleep(poll_interval_seconds)


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        format="%(asctime)s %(levelname)s %(message)s",
        level=getattr(logging, args.log_level),
    )
    settings = Settings()
    config = build_config(settings, args)
    database_url = args.database_url or settings.database_url
    engine = build_engine(database_url)
    init_database(engine)
    session_factory = make_session_factory(engine)

    logging.info(
        "Collection worker started once=%s max_tasks=%s poll_interval=%ss",
        args.once,
        args.max_tasks,
        args.poll_interval_seconds,
    )

    processed_count = run_worker(
        session_factory=session_factory,
        config=config,
        once=args.once,
        max_tasks=args.max_tasks,
        poll_interval_seconds=args.poll_interval_seconds,
    )
    logging.info("Collection worker stopped, processed=%s", processed_count)


if __name__ == "__main__":
    main()
