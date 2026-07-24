from argparse import Namespace
from types import SimpleNamespace
from unittest.mock import MagicMock

from clipboard_sync import cli
from clipboard_sync.state import AppState


def test_handle_push_replaces_stale_device_id_before_upload(monkeypatch):
    state = AppState(
        access_token="access-token",
        refresh_token="refresh-token",
        user_id="user-id",
        client_device_key="existing-key",
        device_id="deleted-device-id",
        device_name="Laptop",
    )
    store = MagicMock()
    store.load.return_value = state
    sync = MagicMock()

    def replace_device_id(current_state, device_name):
        assert current_state.device_id == "deleted-device-id"
        assert current_state.client_device_key == "existing-key"
        assert device_name == "Laptop"
        current_state.device_id = "replacement-device-id"
        return "replacement-device-id"

    sync.ensure_windows_device.side_effect = replace_device_id
    sync.push_clipboard_text.return_value = SimpleNamespace(id="item-id")

    monkeypatch.setattr(cli, "StateStore", MagicMock(return_value=store))
    monkeypatch.setattr(cli, "SupabaseSync", MagicMock(return_value=sync))
    monkeypatch.setattr(cli, "load_config", MagicMock(return_value="config"))
    monkeypatch.setattr(cli, "read_text", MagicMock(return_value="hello"))

    cli.handle_push(Namespace())

    sync.use_session.assert_called_once_with(state)
    sync.ensure_windows_device.assert_called_once_with(state, "Laptop")
    store.save.assert_called_once_with(state)
    assert state.device_id == "replacement-device-id"
    sync.push_clipboard_text.assert_called_once_with(state, "hello")
