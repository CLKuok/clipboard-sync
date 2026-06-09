"""Local state storage for auth tokens and device identity."""

from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


APP_DIR_NAME = "ClipboardSync"
STATE_FILE_NAME = "windows_state.json"


@dataclass
class AppState:
    access_token: str | None = None
    refresh_token: str | None = None
    user_id: str | None = None
    user_email: str | None = None
    client_device_key: str | None = None
    device_id: str | None = None
    device_name: str | None = None

    @property
    def is_logged_in(self) -> bool:
        return bool(self.access_token and self.refresh_token and self.user_id)


def default_state_path() -> Path:
    appdata = os.getenv("APPDATA")
    if appdata:
        base_dir = Path(appdata)
    else:
        base_dir = Path.home() / ".config"
    return base_dir / APP_DIR_NAME / STATE_FILE_NAME


class StateStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_state_path()

    def load(self) -> AppState:
        if not self.path.exists():
            return AppState()

        data = json.loads(self.path.read_text(encoding="utf-8"))
        return AppState(
            access_token=_optional_str(data.get("access_token")),
            refresh_token=_optional_str(data.get("refresh_token")),
            user_id=_optional_str(data.get("user_id")),
            user_email=_optional_str(data.get("user_email")),
            client_device_key=_optional_str(data.get("client_device_key")),
            device_id=_optional_str(data.get("device_id")),
            device_name=_optional_str(data.get("device_name")),
        )

    def save(self, state: AppState) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(asdict(state), indent=2), encoding="utf-8")

    def clear_session(self) -> AppState:
        state = self.load()
        cleared = AppState(client_device_key=state.client_device_key)
        self.save(cleared)
        return cleared


def ensure_client_device_key(state: AppState) -> str:
    if not state.client_device_key:
        state.client_device_key = str(uuid.uuid4())
    return state.client_device_key


def _optional_str(value: Any) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None
