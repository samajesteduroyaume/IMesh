from __future__ import annotations

import secrets
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from ..config import get_settings
from ..registry import SkillRegistry, get_default_registry
from .db import GatewayDB


def create_app(registry: SkillRegistry | None = None) -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="IMesh Gateway", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    db = GatewayDB(settings.gateway_db_path)
    skill_registry = registry or get_default_registry()
    app.state.gateway_db = db

    @app.get("/api/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/checkout/free-key")
    async def free_key() -> dict[str, str]:
        api_key = f"imesh_{secrets.token_urlsafe(24)}"
        db.add_key(api_key)
        return {"api_key": api_key}

    @app.get("/api/v1/skills")
    async def get_skills() -> dict[str, list[str]]:
        return {"skills": [tool["name"] for tool in skill_registry.describe_tools()]}

    @app.get("/api/v1/peers")
    async def get_peers() -> dict[str, list[str]]:
        return {"peers": []}

    @app.post("/api/v1/execute")
    async def execute(request: Request) -> dict[str, object]:
        body = await request.json()
        skill = body.get("skill", "echo")
        try:
            result = skill_registry.call(skill, body.get("payload", {}))
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"unknown skill: {skill}") from exc
        return {
            "status": "ok",
            "skill": skill,
            "payload": body.get("payload", {}),
            "result": result,
        }

    @app.post("/v1/chat/completions")
    async def openai_chat(request: Request) -> dict[str, Any]:
        return {
            "id": "chatcmpl-1",
            "model": "openclaw-mesh",
            "choices": [{"message": {"role": "assistant", "content": "ok"}}],
        }

    @app.post("/v1/messages")
    async def anthropic_messages(request: Request) -> dict[str, str]:
        return {"id": "msg-1", "content": "ok"}

    @app.get("/api/v1/models")
    async def models() -> dict[str, list[str]]:
        return {"data": ["openclaw-mesh"]}

    @app.get("/")
    async def portal() -> str:
        return "<html><body><h1>IMesh Portal</h1><p>Gateway is running.</p><a href='/api/v1/health'>Health</a></body></html>"

    return app
