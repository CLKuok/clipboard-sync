"""Supabase operations for the Windows CLI."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum

import httpx
from supabase import Client, create_client
from supabase_auth.errors import AuthApiError, AuthError, AuthInvalidCredentialsError

from clipboard_sync.config import AppConfig
from clipboard_sync.state import AppState, ensure_client_device_key


class SyncErrorKind(Enum):
    OFFLINE = "offline"
    INVALID_CREDENTIALS = "invalid_credentials"
    AUTHENTICATION_REQUIRED = "authentication_required"
    OPERATION_FAILED = "operation_failed"


class SyncError(RuntimeError):
    """Raised with a safe, actionable message for an expected sync failure."""

    def __init__(self, message: str, kind: SyncErrorKind = SyncErrorKind.OPERATION_FAILED) -> None:
        super().__init__(message)
        self.kind = kind


class AuthenticationRequiredError(SyncError):
    def __init__(self, message: str = "Your session expired. Run login again.") -> None:
        super().__init__(message, SyncErrorKind.AUTHENTICATION_REQUIRED)


@dataclass(frozen=True)
class ClipboardItem:
    id: str
    content: str
    created_at: str
    source_device_id: str | None


class SupabaseSync:
    def __init__(self, config: AppConfig) -> None:
        try:
            self.client: Client = create_client(config.supabase_url, config.supabase_anon_key)
        except Exception as exc:
            raise _friendly_error("start the Supabase client", exc) from exc

    def sign_in(self, email: str, password: str) -> AppState:
        try:
            response = self.client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
        except Exception as exc:
            raise _friendly_error("sign in", exc, signing_in=True) from exc
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
            raise AuthenticationRequiredError("You are not logged in. Run login first.")

        try:
            response = self.client.auth.set_session(state.access_token, state.refresh_token)
        except Exception as exc:
            raise _friendly_error("restore your session", exc) from exc

        session = response.session
        user = response.user
        if session is None or user is None:
            raise AuthenticationRequiredError()

        state.access_token = session.access_token
        state.refresh_token = session.refresh_token
        state.user_id = user.id
        state.user_email = user.email

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
            raise _friendly_error("register this device", exc) from exc

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
        if not content.strip():
            raise SyncError("Clipboard is empty. Nothing to push.")

        payload = {
            "source_device_id": state.device_id,
            "content": content,
            "content_type": "text/plain",
        }

        try:
            response = self.client.table("clipboard_items").insert(payload).execute()
        except Exception as exc:
            raise _friendly_error("push clipboard text", exc) from exc

        return _clipboard_item_from_row(_first_row(response.data, "clipboard push"))

    def pull_latest_clipboard_text(self) -> ClipboardItem | None:
        try:
            response = (
                self.client.table("clipboard_items")
                .select("id, content, created_at, source_device_id")
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
        except Exception as exc:
            raise _friendly_error("pull clipboard text", exc) from exc

        if not response.data:
            return None

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


def _friendly_error(action: str, error: Exception, *, signing_in: bool = False) -> SyncError:
    errors = list(_error_chain(error))

    if any(isinstance(item, (httpx.TransportError, ConnectionError, TimeoutError)) for item in errors):
        return SyncError(
            "You appear to be offline. Check your connection and try again.",
            SyncErrorKind.OFFLINE,
        )

    auth_error = next((item for item in errors if isinstance(item, AuthError)), None)
    if signing_in and isinstance(auth_error, (AuthApiError, AuthInvalidCredentialsError)):
        code = getattr(auth_error, "code", None)
        status = getattr(auth_error, "status", None)
        if code == "invalid_credentials" or status in (400, 401):
            return SyncError(
                "Email or password is incorrect.",
                SyncErrorKind.INVALID_CREDENTIALS,
            )

    if isinstance(auth_error, AuthError):
        code = getattr(auth_error, "code", None)
        status = getattr(auth_error, "status", None)
        if status in (401, 403) or code in {
            "bad_jwt",
            "invalid_jwt",
            "no_authorization",
            "session_not_found",
            "user_not_found",
        }:
            return AuthenticationRequiredError()

    return SyncError(f"Could not {action}. Please try again.")


def _error_chain(error: BaseException):
    seen: set[int] = set()
    current: BaseException | None = error
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        yield current
        current = current.__cause__ or current.__context__
