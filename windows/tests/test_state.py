from clipboard_sync.state import AppState, StateStore, ensure_client_device_key


def test_state_round_trip(tmp_path):
    store = StateStore(tmp_path / "state.json")
    state = AppState(
        access_token="access",
        refresh_token="refresh",
        user_id="user-id",
        user_email="user@example.com",
        client_device_key="device-key",
        device_id="device-id",
        device_name="Laptop",
    )

    store.save(state)

    loaded = store.load()
    assert loaded.access_token == "access"
    assert loaded.refresh_token == "refresh"
    assert loaded.user_id == "user-id"
    assert loaded.user_email == "user@example.com"
    assert loaded.client_device_key == "device-key"
    assert loaded.device_id == "device-id"
    assert loaded.device_name == "Laptop"


def test_clear_session_keeps_client_device_key(tmp_path):
    store = StateStore(tmp_path / "state.json")
    store.save(
        AppState(
            access_token="access",
            refresh_token="refresh",
            user_id="user-id",
            client_device_key="device-key",
            device_id="device-id",
        )
    )

    cleared = store.clear_session()

    assert not cleared.is_logged_in
    assert cleared.client_device_key == "device-key"
    assert cleared.device_id is None


def test_ensure_client_device_key_reuses_existing_value():
    state = AppState(client_device_key="existing")

    assert ensure_client_device_key(state) == "existing"


def test_ensure_client_device_key_creates_value():
    state = AppState()

    key = ensure_client_device_key(state)

    assert key
    assert state.client_device_key == key
