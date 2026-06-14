from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLUGIN_HUB_")

    database_url: str = "sqlite+pysqlite:///./plugin_hub.db"
    collection_task_max_attempts: int = 3
    collection_task_retry_delay_seconds: int = 300
    collection_task_claim_ttl_seconds: int = 900
    collection_task_worker_id: str = "api-worker"
