"""Supabase operations for the Windows CLI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from supabase import Client, create_client

from clipboard_sync.config import AppConfig
from clipboard_sync.state import AppState, ensure_client_device_key


class SyncError(RuntimeError):
    """Raised when a Supabase sync operation fails."""


@dataclass(frozen=True)
class ClipboardItem:
    id: str
    content: str
    created_at: str
    source_device_id: str | None


class SupabaseSync:
    def __init__(self, config: AppConfig) -> None:
        self.client: Client = create_client(config.supabase_url, config.supabase_anon_key)

    def sign_in(self, email: str, password: str) -> AppState:
        response = self.client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        session = response.session
        user = response.user

        if session is None or user is None:
            raise SyncError("Login failed: Supabase did not return a session.")

        return AppState(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user_id=user.id,
            user_email=user.email,
        )

    def use_session(self, state: AppState) -> None:
        if not state.access_token or not state.refresh_token:
            raise SyncError("You are not logged in. Run login first.")
        self.client.auth.set_session(state.access_token, state.refresh_token)

    def ensure_windows_device(self, state: AppState, device_name: str) -> str:
        if not state.user_id:
            raise SyncError("You are not logged in. Run login first.")

        client_device_key = ensure_client_device_key(state)
        payload = {
            "client_device_key": client_device_key,
            "name": device_name,
            "platform": "windows",
            "last_seen_at": datetime.now(UTC).isoformat(),
        }

        try:
            response = (
                self.client.table("devices")
                .upsert(payload, on_conflict="user_id,client_device_key")
                .execute()
            )
        except Exception as exc:  # Supabase exceptions vary by transport/version.
            raise SyncError(f"Could not register device: {exc}") from exc

        row = _first_row(response.data, "device registration")
        device_id = row.get("id")
        if not isinstance(device_id, str) or not device_id:
            raise SyncError("Device registration did not return a device ID.")

        state.device_id = device_id
        state.device_name = device_name
        return device_id

    def push_clipboard_text(self, state: AppState, content: str) -> ClipboardItem:
        if not state.device_id:
            raise SyncError("No registered device found. Run login first.")
        if not content:
            raise SyncError("Clipboard is empty. Nothing to push.")

        payload = {
            "source_device_id": state.device_id,
            "content": content,
            "content_type": "text/plain",
        }

        try:
            response = self.client.table("clipboard_items").insert(payload).execute()
        except Exception as exc:
            raise SyncError(f"Could not push clipboard text: {exc}") from exc

        return _clipboard_item_from_row(_first_row(response.data, "clipboard push"))

    def pull_latest_clipboard_text(self) -> ClipboardItem:
        try:
            response = (
                self.client.table("clipboard_items")
                .select("id, content, created_at, source_device_id")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise SyncError(f"Could not pull clipboard text: {exc}") from exc

        if not response.data:
            raise SyncError("No clipboard items found for this user.")

        return _clipboard_item_from_row(_first_row(response.data, "clipboard pull"))


def _first_row(data: object, action: str) -> dict[str, object]:
    if not isinstance(data, list) or not data:
        raise SyncError(f"No row returned after {action}.")
    row = data[0]
    if not isinstance(row, dict):
        raise SyncError(f"Unexpected row returned after {action}.")
    return row


def _clipboard_item_from_row(row: dict[str, object]) -> ClipboardItem:
    item_id = row.get("id")
    content = row.get("content")
    created_at = row.get("created_at")
    source_device_id = row.get("source_device_id")

    if not isinstance(item_id, str):
        raise SyncError("Clipboard item row is missing an ID.")
    if not isinstance(content, str):
        raise SyncError("Clipboard item row is missing text content.")
    if not isinstance(created_at, str):
        raise SyncError("Clipboard item row is missing created_at.")
    if source_device_id is not None and not isinstance(source_device_id, str):
        raise SyncError("Clipboard item row has an invalid source_device_id.")

    return ClipboardItem(
        id=item_id,
        content=content,
        created_at=created_at,
        source_device_id=source_device_id,
    )
