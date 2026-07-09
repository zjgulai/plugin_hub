from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLUGIN_HUB_")

    database_url: str = "sqlite+pysqlite:///./plugin_hub.db"
    collection_task_max_attempts: int = 3
    collection_task_retry_delay_seconds: int = 300
    collection_task_claim_ttl_seconds: int = 900
    collection_task_worker_id: str = "api-worker"
    reddit_client_id: str | None = None
    reddit_client_secret: str | None = None
    reddit_user_agent: str = "PluginHubVOC/0.1 server-side capture"
    instagram_graph_access_token: str | None = None
    instagram_graph_live_read_enabled: bool = False
    instagram_graph_api_version: str = "v25.0"
    instagram_graph_api_base_url: str = "https://graph.facebook.com"
    instagram_graph_comment_limit: int = 50
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:8010",
            "http://127.0.0.1:8010",
            "https://plugin.lute-tlz-dddd.top",
            "https://reddit.com",
            "https://www.reddit.com",
            "https://old.reddit.com",
            "https://www.amazon.com",
        ]
    )
    cors_allow_origin_regex: str | None = r"^chrome-extension://[a-z]{32}$"
