from openclaw_mesh.config import Settings, get_settings, reload_settings, reset_settings


def test_settings_defaults():
    settings = Settings()
    assert settings.default_port == 8765
    assert settings.node_name == "openclaw-node"


def test_settings_singleton_resettable():
    first = get_settings()
    first.node_name = "alpha"
    second = reload_settings()
    assert second.node_name == "openclaw-node"
    assert get_settings().node_name == "openclaw-node"
    reset_settings()
