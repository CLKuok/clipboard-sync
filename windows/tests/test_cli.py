from argparse import Namespace
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from clipboard_sync import cli
from clipboard_sync.state import AppState
from clipboard_sync.supabase_client import AuthenticationRequiredError, SyncError


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


def test_handle_pull_empty_result_does_not_change_clipboard(monkeypatch, capsys):
    state = AppState(access_token="access", refresh_token="refresh", user_id="user-id")
    store = MagicMock()
    store.load.return_value = state
    sync = MagicMock()
    sync.pull_latest_clipboard_text.return_value = None
    write_text = MagicMock()

    monkeypatch.setattr(cli, "StateStore", MagicMock(return_value=store))
    monkeypatch.setattr(cli, "SupabaseSync", MagicMock(return_value=sync))
    monkeypatch.setattr(cli, "load_config", MagicMock(return_value="config"))
    monkeypatch.setattr(cli, "write_text", write_text)

    cli.handle_pull(Namespace())

    write_text.assert_not_called()
    assert "No synced text yet" in capsys.readouterr().out


def test_expired_saved_session_is_cleared_but_device_key_is_preserved(monkeypatch):
    state = AppState(
        access_token="expired",
        refresh_token="expired",
        user_id="user-id",
        client_device_key="stable-key",
    )
    store = MagicMock()
    store.load.return_value = state
    sync = MagicMock()
    sync.use_session.side_effect = AuthenticationRequiredError()

    monkeypatch.setattr(cli, "StateStore", MagicMock(return_value=store))
    monkeypatch.setattr(cli, "SupabaseSync", MagicMock(return_value=sync))
    monkeypatch.setattr(cli, "load_config", MagicMock(return_value="config"))

    with pytest.raises(AuthenticationRequiredError):
        cli.handle_pull(Namespace())

    store.clear_session.assert_called_once_with()


def test_main_prints_expected_sync_failure_without_traceback(monkeypatch, capsys):
    parser = MagicMock()
    parser.parse_args.return_value = Namespace(
        handler=MagicMock(side_effect=SyncError("Friendly failure"))
    )
    monkeypatch.setattr(cli, "build_parser", MagicMock(return_value=parser))

    with pytest.raises(SystemExit) as caught:
        cli.main()

    assert caught.value.code == 1
    assert capsys.readouterr().err == "Error: Friendly failure\n"
