from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from clipboard_sync.gui import COLORS, DARK_COLORS, LIGHT_COLORS, DesktopController, default_device_name
from clipboard_sync.state import AppState
from clipboard_sync.supabase_client import AuthenticationRequiredError


def _controller(state=None):
    store = MagicMock()
    store.load.return_value = state or AppState(client_device_key="stable-key")
    sync = MagicMock()
    controller = DesktopController(
        store=store,
        config_loader=MagicMock(return_value="config"),
        sync_factory=MagicMock(return_value=sync),
        clipboard_reader=MagicMock(return_value="clipboard text"),
        clipboard_writer=MagicMock(),
    )
    return controller, store, sync


def test_gui_login_reuses_install_key_and_registers_device():
    controller, store, sync = _controller()
    signed_in = AppState(
        access_token="access",
        refresh_token="refresh",
        user_id="user-id",
        user_email="person@example.com",
    )
    sync.sign_in.return_value = signed_in

    state = controller.login(" person@example.com ", "password", "Laptop Windows")

    sync.sign_in.assert_called_once_with("person@example.com", "password")
    sync.ensure_windows_device.assert_called_once_with(state, "Laptop Windows")
    assert state.client_device_key == "stable-key"
    store.save.assert_called_with(state)
    assert controller.is_logged_in


def test_gui_restores_session_and_reuses_device():
    state = AppState(
        access_token="access",
        refresh_token="refresh",
        user_id="user-id",
        client_device_key="stable-key",
    )
    controller, store, sync = _controller(state)

    restored = controller.restore("Laptop Windows")

    assert restored is state
    sync.use_session.assert_called_once_with(state)
    sync.ensure_windows_device.assert_called_once_with(state, "Laptop Windows")
    store.save.assert_called_with(state)


def test_gui_push_uses_existing_services_and_clipboard():
    state = AppState(
        access_token="access",
        refresh_token="refresh",
        user_id="user-id",
        device_id="device-id",
    )
    controller, _, sync = _controller(state)
    controller.sync = sync

    content = controller.push("Laptop Windows")

    assert content == "clipboard text"
    sync.ensure_windows_device.assert_called_once_with(state, "Laptop Windows")
    sync.push_clipboard_text.assert_called_once_with(state, "clipboard text")


def test_gui_push_can_use_entered_text_without_reading_clipboard():
    state = AppState(
        access_token="access",
        refresh_token="refresh",
        user_id="user-id",
        device_id="device-id",
    )
    controller, _, sync = _controller(state)
    controller.sync = sync

    content = controller.push("Laptop Windows", "text entered in the app")

    assert content == "text entered in the app"
    controller.clipboard_reader.assert_not_called()
    sync.push_clipboard_text.assert_called_once_with(state, "text entered in the app")


def test_gui_empty_pull_does_not_change_clipboard():
    state = AppState(access_token="access", refresh_token="refresh", user_id="user-id")
    controller, _, sync = _controller(state)
    controller.sync = sync
    sync.pull_latest_clipboard_text.return_value = None

    assert controller.pull() is None
    controller.clipboard_writer.assert_not_called()


def test_gui_pull_waits_for_explicit_copy_action():
    state = AppState(access_token="access", refresh_token="refresh", user_id="user-id")
    controller, _, sync = _controller(state)
    controller.sync = sync
    item = SimpleNamespace(content="latest text")
    sync.pull_latest_clipboard_text.return_value = item

    assert controller.pull() is item
    controller.clipboard_writer.assert_not_called()

    assert controller.copy_to_clipboard(item.content) == "latest text"
    controller.clipboard_writer.assert_called_once_with("latest text")


def test_gui_expired_session_clears_local_account():
    state = AppState(access_token="expired", refresh_token="expired", user_id="user-id")
    controller, store, sync = _controller(state)
    controller.sync = sync
    cleared = AppState(client_device_key="stable-key")
    store.clear_session.return_value = cleared
    sync.use_session.side_effect = AuthenticationRequiredError()

    with pytest.raises(AuthenticationRequiredError):
        controller.pull()

    assert controller.state is cleared
    assert controller.sync is None


def test_gui_logout_clears_session_and_keeps_returned_install_state():
    state = AppState(access_token="access", refresh_token="refresh", user_id="user-id")
    controller, store, sync = _controller(state)
    controller.sync = sync
    cleared = AppState(client_device_key="stable-key")
    store.clear_session.return_value = cleared

    controller.logout()

    assert controller.state is cleared
    assert controller.sync is None
    store.clear_session.assert_called_once_with()


def test_gui_theme_has_distinct_feedback_colours():
    assert COLORS["success"] != COLORS["error"]
    assert COLORS["info_background"] != COLORS["error_background"]
    assert DARK_COLORS["background"] != LIGHT_COLORS["background"]
    assert DARK_COLORS["surface"] != LIGHT_COLORS["surface"]


def test_default_device_name_is_user_readable():
    assert default_device_name().endswith((" Windows", "Windows Device"))
