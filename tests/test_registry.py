import pytest

from openclaw_mesh.registry import SkillRegistry, get_default_registry


@pytest.fixture
def registry():
    return SkillRegistry()


def test_registry_register_sync(registry):
    @registry.register("echo")
    def echo(payload=None):
        return {"payload": payload}

    assert registry.get("echo").name == "echo"
    assert registry.call("echo", {"payload": {"ok": True}})["payload"] == {"ok": True}


def test_registry_builtin_skills():
    registry = get_default_registry()
    assert "echo" in registry
    assert "_health" in registry
    assert registry.call("_health") == {"status": "ok"}


def test_registry_describe_tools():
    registry = get_default_registry()
    tools = registry.describe_tools()
    assert any(tool["name"] == "echo" for tool in tools)
    assert all("expose_remote" in tool for tool in tools)
