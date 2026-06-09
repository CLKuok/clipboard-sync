"""Environment configuration for the Windows CLI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    """Raised when required configuration is missing."""


@dataclass(frozen=True)
class AppConfig:
    supabase_url: str
    supabase_anon_key: str


def load_config() -> AppConfig:
    """Load Supabase configuration from windows/.env or the process environment."""
    env_path = Path(__file__).resolve().parents[1] / ".env"
    load_dotenv(env_path)

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_anon_key = os.getenv("SUPABASE_ANON_KEY", "").strip()

    missing = []
    if not supabase_url:
        missing.append("SUPABASE_URL")
    if not supabase_anon_key:
        missing.append("SUPABASE_ANON_KEY")

    if missing:
        missing_list = ", ".join(missing)
        raise ConfigError(
            f"Missing {missing_list}. Copy windows/.env.example to windows/.env and fill it in."
        )

    return AppConfig(
        supabase_url=supabase_url,
        supabase_anon_key=supabase_anon_key,
    )
