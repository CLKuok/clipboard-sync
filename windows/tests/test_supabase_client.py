from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from supabase_auth.errors import AuthApiError

from clipboard_sync.config import AppConfig
from clipboard_sync.state import AppState
from clipboard_sync.supabase_client import (
    AuthenticationRequiredError,
    SupabaseSync,
    SyncError,
    SyncErrorKind,
    _clipboard_item_from_row,
)


def _make_sync(monkeypatch):
    client = MagicMock()
    create_client = MagicMock(return_value=client)
    monkeypatch.setattr("clipboard_sync.supabase_client.create_client", create_client)
    sync = SupabaseSync(AppConfig("https://example.supabase.co", "anon-key"))
    return sync, client


def test_clipboard_item_from_row():
    item = _clipboard_item_from_row(
        {
            "id": "item-id",
            "content": "hello",
            "created_at": "2026-06-09T00:00:00Z",
            "source_device_id": "device-id",
        }
    )

    assert item.id == "item-id"
    assert item.content == "hello"
    assert item.created_at == "2026-06-09T00:00:00Z"
    assert item.source_device_id == "device-id"


def test_ensure_windows_device_creates_device_and_saves_returned_id(monkeypatch):
    sync, client = _make_sync(monkeypatch)
    query = client.table.return_value
    query.upsert.return_value.execute.return_value = SimpleNamespace(
        data=[{"id": "new-device-id"}]
    )
    state = AppState(user_id="user-id")

    device_id = sync.ensure_windows_device(state, "Laptop")

    client.table.assert_called_once_with("devices")
    payload = query.upsert.call_args.args[0]
    assert payload["client_device_key"] == state.client_device_key
    assert payload["client_device_key"]
    assert payload["name"] == "Laptop"
    assert payload["platform"] == "windows"
    assert payload["last_seen_at"]
    assert query.upsert.call_args.kwargs == {
        "on_conflict": "user_id,client_device_key"
    }
    assert device_id == "new-device-id"
    assert state.device_id == "new-device-id"
    assert state.device_name == "Laptop"


def test_ensure_windows_device_reuses_existing_client_device_key(monkeypatch):
    sync, client = _make_sync(monkeypatch)
    query = client.table.return_value
    query.upsert.return_value.execute.side_effect = [
        SimpleNamespace(data=[{"id": "existing-device-id"}]),
        SimpleNamespace(data=[{"id": "existing-device-id"}]),
    ]
    state = AppState(user_id="user-id", client_device_key="existing-key")

    first_device_id = sync.ensure_windows_device(state, "Laptop")
    second_device_id = sync.ensure_windows_device(state, "Laptop")

    assert first_device_id == "existing-device-id"
    assert second_device_id == "existing-device-id"
    assert state.client_device_key == "existing-key"
    assert query.upsert.call_count == 2
    for upsert_call in query.upsert.call_args_list:
        assert upsert_call.args[0]["client_device_key"] == "existing-key"
        assert upsert_call.kwargs == {"on_conflict": "user_id,client_device_key"}


def test_push_clipboard_text_inserts_text_for_current_device(monkeypatch):
    sync, client = _make_sync(monkeypatch)
    query = client.table.return_value
    query.insert.return_value.execute.return_value = SimpleNamespace(
        data=[
            {
                "id": "item-id",
                "content": "hello",
                "created_at": "2026-06-09T00:00:00Z",
                "source_device_id": "device-id",
            }
        ]
    )
    state = AppState(device_id="device-id")

    item = sync.push_clipboard_text(state, "hello")

    client.table.assert_called_once_with("clipboard_items")
    query.insert.assert_called_once_with(
        {
            "source_device_id": "device-id",
            "content": "hello",
            "content_type": "text/plain",
        }
    )
    assert item.id == "item-id"
    assert item.content == "hello"
    assert item.source_device_id == "device-id"


def test_pull_latest_clipboard_text_fetches_newest_item(monkeypatch):
    sync, client = _make_sync(monkeypatch)
    query = client.table.return_value
    select_query = query.select.return_value
    order_query = select_query.order.return_value
    limit_query = order_query.limit.return_value
    limit_query.execute.return_value = SimpleNamespace(
        data=[
            {
                "id": "latest-item-id",
                "content": "latest text",
                "created_at": "2026-06-09T00:00:00Z",
                "source_device_id": "device-id",
            }
        ]
    )

    item = sync.pull_latest_clipboard_text()

    client.table.assert_called_once_with("clipboard_items")
    query.select.assert_called_once_with(
        "id, content, created_at, source_device_id"
    )
    select_query.order.assert_called_once_with("created_at", desc=True)
    order_query.limit.assert_called_once_with(1)
    assert item.id == "latest-item-id"
    assert item.content == "latest text"


def test_pull_latest_clipboard_text_returns_none_when_empty(monkeypatch):
    sync, client = _make_sync(monkeypatch)
    client.table.return_value.select.return_value.order.return_value.limit.return_value.execute.return_value = SimpleNamespace(data=[])

    assert sync.pull_latest_clipboard_text() is None


def test_push_rejects_whitespace_only_text(monkeypatch):
    sync, client = _make_sync(monkeypatch)
    state = AppState(device_id="device-id")

    with pytest.raises(SyncError, match="Clipboard is empty"):
        sync.push_clipboard_text(state, "  \n\t  ")

    client.table.assert_not_called()


def test_sign_in_maps_invalid_credentials(monkeypatch):
    sync, client = _make_sync(monkeypatch)
    client.auth.sign_in_with_password.side_effect = AuthApiError(
        "Invalid login credentials", 400, "invalid_credentials"
    )

    with pytest.raises(SyncError) as caught:
        sync.sign_in("person@example.com", "wrong")

    assert caught.value.kind is SyncErrorKind.INVALID_CREDENTIALS
    assert str(caught.value) == "Email or password is incorrect."


def test_pull_maps_transport_failure_to_offline_message(monkeypatch):
    sync, client = _make_sync(monkeypatch)
    request = httpx.Request("GET", "https://example.supabase.co")
    client.table.return_value.select.return_value.order.return_value.limit.return_value.execute.side_effect = httpx.ConnectError(
        "synthetic network failure", request=request
    )

    with pytest.raises(SyncError) as caught:
        sync.pull_latest_clipboard_text()

    assert caught.value.kind is SyncErrorKind.OFFLINE
    assert "offline" in str(caught.value).lower()
    assert "synthetic" not in str(caught.value)


def test_use_session_maps_expired_session(monkeypatch):
    sync, client = _make_sync(monkeypatch)
    client.auth.set_session.side_effect = AuthApiError(
        "JWT expired", 401, "invalid_jwt"
    )
    state = AppState(access_token="access", refresh_token="refresh", user_id="user")

    with pytest.raises(AuthenticationRequiredError, match="session expired"):
        sync.use_session(state)
