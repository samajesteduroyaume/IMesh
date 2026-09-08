from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OPENCLAW_",
        env_file=".env",
        extra="ignore",
        case_sensitive=False,
    )

    node_name: str = Field(default="openclaw-node")
    client_name: str = Field(default="openclaw-client")
    default_host: str = Field(default="127.0.0.1")
    default_port: int = Field(default=8765)
    wan_enabled: bool = Field(default=False)
    mdns_enabled: bool = Field(default=True)
    dht_enabled: bool = Field(default=False)
    quic_enabled: bool = Field(default=False)
    gossipsub_enabled: bool = Field(default=False)
    psk: str | None = Field(default=None)
    e2ee_enabled: bool = Field(default=False)
    identity_key_path: str = Field(default="./.openclaw_identity.pem")
    trust_store_path: str = Field(default="./.openclaw_trust_store.json")
    max_active_tasks: int = Field(default=32)
    max_queued_tasks: int = Field(default=128)
    task_timeout: float = Field(default=30.0)
    max_output_bytes: int = Field(default=1_000_000)
    gateway_host: str = Field(default="127.0.0.1")
    gateway_port: int = Field(default=8000)
    gateway_db_path: str = Field(default="./openclaw_gateway.db")
    peer_ttl_seconds: int = Field(default=120)
    log_level: str = Field(default="INFO")

    @classmethod
    def from_env(cls) -> "Settings":
        return cls()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def reload_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()


def reset_settings() -> Settings:
    get_settings.cache_clear()
    return get_settings()
