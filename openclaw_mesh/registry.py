from __future__ import annotations

import asyncio
import inspect
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SkillDefinition:
    name: str
    description: str
    func: Callable[..., Any]
    schema: type | None = None
    expose_remote: bool = True

    def to_tool(self) -> dict[str, Any]:
        tool = {
            "name": self.name,
            "description": self.description,
            "type": "function",
            "expose_remote": self.expose_remote,
        }
        if self.schema is not None:
            tool["input_schema"] = getattr(self.schema, "model_json_schema", lambda: {})()
        return tool


class SkillRegistry:
    def __init__(self) -> None:
        self._skills: dict[str, SkillDefinition] = {}

    def register(self, name: str | None = None, description: str = "", schema: type | None = None, expose_remote: bool = True):
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            skill_name = name or func.__name__
            self._skills[skill_name] = SkillDefinition(
                name=skill_name,
                description=description or getattr(func, "__doc__", "") or "",
                func=func,
                schema=schema,
                expose_remote=expose_remote,
            )
            return func

        return decorator

    def register_dict(self, definition: dict[str, Any]) -> None:
        for key, value in definition.items():
            if not isinstance(value, dict):
                raise TypeError("Skill definitions must be dictionaries")
            self._skills[key] = SkillDefinition(
                name=value.get("name", key),
                description=value.get("description", ""),
                func=value.get("func"),
                schema=value.get("schema"),
                expose_remote=value.get("expose_remote", True),
            )

    def get(self, name: str) -> SkillDefinition:
        if name not in self._skills:
            raise KeyError(name)
        return self._skills[name]

    def __contains__(self, name: str) -> bool:
        return name in self._skills

    def list(self) -> list[SkillDefinition]:
        return list(self._skills.values())

    def describe_tools(self) -> list[dict[str, Any]]:
        return [skill.to_tool() for skill in self._skills.values() if skill.expose_remote]

    def call(self, name: str, payload: dict[str, Any] | None = None) -> Any:
        skill = self.get(name)
        payload = payload or {}

        def invoke() -> Any:
            try:
                return skill.func(**payload)
            except TypeError:
                try:
                    return skill.func(payload)
                except TypeError:
                    raise

        result = invoke()
        if inspect.isawaitable(result):
            return asyncio.get_event_loop().run_until_complete(result)
        if inspect.isgenerator(result):
            return list(result)
        if isinstance(result, AsyncGenerator):
            async def _collect() -> list[Any]:
                items: list[Any] = []
                async for item in result:
                    items.append(item)
                return items

            return asyncio.get_event_loop().run_until_complete(_collect())
        return result


def skill(name: str, description: str = "", schema: type | None = None, expose_remote: bool = True):
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        func._skill_name = name
        func._skill_description = description
        func._skill_schema = schema
        func._skill_expose_remote = expose_remote
        return func

    return decorator


def _register_builtin_skills(registry: SkillRegistry) -> None:
    @registry.register(name="echo", description="Echo back input payload")
    def echo(payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {"payload": payload or {}}

    @registry.register(name="openclaw_info", description="Return OpenClaw metadata")
    def openclaw_info() -> dict[str, Any]:
        return {"name": "openclaw-mesh", "version": "0.1.0"}

    @registry.register(name="system_info", description="Return basic system information")
    def system_info() -> dict[str, Any]:
        import platform

        return {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
        }

    registry.register(name="_describe_skills", description="Describe available skills")(lambda: registry.describe_tools())
    registry.register(name="_health", description="Health check")(lambda: {"status": "ok"})


_DEFAULT_REGISTRY = SkillRegistry()
_register_builtin_skills(_DEFAULT_REGISTRY)


def get_default_registry() -> SkillRegistry:
    return _DEFAULT_REGISTRY
