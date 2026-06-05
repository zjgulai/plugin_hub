from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PLUGIN_HUB_")

    database_url: str = "sqlite+pysqlite:///:memory:"
