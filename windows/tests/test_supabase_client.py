from clipboard_sync.supabase_client import _clipboard_item_from_row


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
