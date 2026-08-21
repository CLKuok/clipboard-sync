"""Environment configuration for the Windows CLI."""

from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

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

    _validate_supabase_url(supabase_url)
    _validate_public_key(supabase_anon_key)

    return AppConfig(
        supabase_url=supabase_url,
        supabase_anon_key=supabase_anon_key,
    )


def _validate_supabase_url(value: str) -> None:
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.path not in ("", "/")
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ConfigError(
            "SUPABASE_URL must be the HTTPS project base URL, such as "
            "https://your-project-ref.supabase.co."
        )


def _validate_public_key(value: str) -> None:
    lowered = value.lower()
    if lowered.startswith("sb_secret_") or _legacy_jwt_role(value) == "service_role":
        raise ConfigError(
            "SUPABASE_ANON_KEY must be a publishable or legacy anon key. "
            "Never use a secret or service-role key in a client app."
        )


def _legacy_jwt_role(value: str) -> str | None:
    parts = value.split(".")
    if len(parts) != 3:
        return None

    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        decoded = base64.urlsafe_b64decode(payload.encode("ascii"))
        data = json.loads(decoded)
    except (ValueError, UnicodeError, json.JSONDecodeError):
        return None

    role = data.get("role") if isinstance(data, dict) else None
    return role if isinstance(role, str) else None
