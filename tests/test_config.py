import importlib

import pytest

from core import config


@pytest.fixture(autouse=True)
def _restore_config():
    """Reload the module with the original environment after each test."""
    yield
    importlib.reload(config)


def test_defaults_are_snowflakes():
    assert config.GUILD_ID > 0
    assert config.QUEUE_CHANNEL_ID > 0
    assert config.SUPPORT_CHANNEL_ID > 0


def test_sync_guild_ids_uses_dev_guild():
    assert config.sync_guild_ids() == [config.DEV_GUILD_ID]


def test_sync_guild_ids_global_when_zero(monkeypatch):
    monkeypatch.setenv("DEV_GUILD_ID", "0")
    reloaded = importlib.reload(config)
    assert reloaded.sync_guild_ids() is None


def test_env_override(monkeypatch):
    monkeypatch.setenv("QUEUE_CHANNEL_ID", "123456789012345678")
    reloaded = importlib.reload(config)
    assert reloaded.QUEUE_CHANNEL_ID == 123456789012345678


def test_invalid_id_raises(monkeypatch):
    monkeypatch.setenv("QUEUE_CHANNEL_ID", "not-a-number")
    with pytest.raises(ValueError):
        importlib.reload(config)


def test_warning_role_is_disabled_by_default():
    assert config.WARNING_ROLE_ID == 0


def test_dev_ids_are_parsed(monkeypatch):
    monkeypatch.setenv("DEV_USER_IDS", "1, 2,3")
    reloaded = importlib.reload(config)
    assert reloaded.DEV_USER_IDS == (1, 2, 3)
