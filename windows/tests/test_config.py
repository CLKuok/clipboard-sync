import base64
import json

import pytest

from clipboard_sync.config import ConfigError, load_config


def _set_config(monkeypatch, url="https://example.supabase.co", key="sb_publishable_example"):
    monkeypatch.setenv("SUPABASE_URL", url)
    monkeypatch.setenv("SUPABASE_ANON_KEY", key)


def _jwt_with_role(role):
    payload = base64.urlsafe_b64encode(json.dumps({"role": role}).encode()).decode().rstrip("=")
    return f"e30.{payload}.signature"


def test_load_config_accepts_project_base_url_and_public_key(monkeypatch):
    _set_config(monkeypatch)

    config = load_config()

    assert config.supabase_url == "https://example.supabase.co"
    assert config.supabase_anon_key == "sb_publishable_example"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.supabase.co",
        "https://example.supabase.co/rest/v1",
        "https://example.supabase.co?secret=value",
    ],
)
def test_load_config_rejects_non_base_or_insecure_url(monkeypatch, url):
    _set_config(monkeypatch, url=url)

    with pytest.raises(ConfigError, match="HTTPS project base URL"):
        load_config()


@pytest.mark.parametrize(
    "key",
    ["sb_secret_example", _jwt_with_role("service_role")],
)
def test_load_config_rejects_secret_keys(monkeypatch, key):
    _set_config(monkeypatch, key=key)

    with pytest.raises(ConfigError, match="Never use a secret or service-role key"):
        load_config()
