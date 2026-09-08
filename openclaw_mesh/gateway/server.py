from __future__ import annotations

import secrets
import time
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from ..config import get_settings
from ..discovery import MeshDiscovery, PeerInfo
from ..registry import SkillRegistry, get_default_registry
from .db import GatewayDB


def _default_models() -> list[dict[str, Any]]:
    now = int(time.time())
    return [
        {
            "id": "openclaw-mesh",
            "object": "model",
            "created": now,
            "owned_by": "IMesh",
            "permission": [],
            "root": "openclaw-mesh",
            "parent": None,
        }
    ]


def _model_listing() -> dict[str, Any]:
    return {"object": "list", "data": _default_models()}


def _portal_summary(models: list[dict[str, Any]], peers: list[dict[str, Any]], logs: list[dict[str, Any]]) -> dict[str, Any]:
    reachable_peers = sum(1 for peer in peers if peer.get("reachable", False))
    skills = sorted({skill for peer in peers for skill in peer.get("skills", [])})
    return {
        "models_count": len(models),
        "peers_count": len(peers),
        "reachable_peers": reachable_peers,
        "unreachable_peers": max(len(peers) - reachable_peers, 0),
        "skills_count": len(skills),
        "log_count": len(logs),
        "last_updated": int(time.time()),
    }


def _stringify_result(value: Any) -> str:
    if isinstance(value, (dict, list)):
        return __import__("json").dumps(value, indent=2, ensure_ascii=False)
    return str(value)


def _infer_skill_from_prompt(prompt: str, registry: SkillRegistry) -> str | None:
    stripped = prompt.strip()
    if stripped.startswith("skill:"):
        skill_name = stripped.split(":", 1)[1].strip()
        if skill_name:
            return skill_name
    if stripped.startswith("call "):
        skill_name = stripped.split(" ", 1)[1].strip()
        if skill_name and skill_name in registry:
            return skill_name
    if stripped in registry:
        return stripped
    return None


def _extract_last_user_message(messages: list[dict[str, Any]] | None) -> str:
    if not messages:
        return ""
    for message in reversed(messages):
        if message.get("role") == "user":
            content = message.get("content", "")
            if isinstance(content, list):
                return " ".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
            return str(content)
    last_message = messages[-1]
    content = last_message.get("content", "")
    if isinstance(content, list):
        return " ".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    return str(content)


def create_app(registry: SkillRegistry | None = None, discovery: MeshDiscovery | None = None) -> FastAPI:
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
    app.state.discovery = discovery or MeshDiscovery(
        node_name=settings.node_name,
        port=settings.default_port,
        enabled=settings.mdns_enabled,
        peer_ttl_seconds=settings.peer_ttl_seconds,
    )
    app.state.logs: list[dict[str, Any]] = [
        {
            "timestamp": int(time.time()),
            "level": "info",
            "message": "IMesh gateway initialized",
        }
    ]

    local_peer = PeerInfo(
        name=settings.node_name,
        host=settings.default_host,
        port=settings.default_port,
        skills=sorted(skill_registry._skills.keys()),
        protocol_version="0.1.0",
    )
    app.state.discovery.add_peer(local_peer)

    def add_log(level: str, message: str, **extra: Any) -> None:
        app.state.logs.append(
            {
                "timestamp": int(time.time()),
                "level": level,
                "message": message,
                **extra,
            }
        )
        if len(app.state.logs) > 200:
            app.state.logs = app.state.logs[-200:]

    def collect_peers() -> list[dict[str, Any]]:
        peers = []
        seen: set[str] = set()
        for peer in app.state.discovery.discover_now():
            payload = {
                "name": peer.name,
                "host": peer.host,
                "port": peer.port,
                "skills": peer.skills,
                "reachable": getattr(peer, "reachable", True),
                "protocol_version": peer.protocol_version,
                "last_seen": getattr(peer, "last_seen", int(time.time())),
            }
            peers.append(payload)
            seen.add(peer.name)
        if settings.node_name not in seen:
            peers.append(
                {
                    "name": settings.node_name,
                    "host": settings.default_host,
                    "port": settings.default_port,
                    "skills": sorted(skill_registry._skills.keys()),
                    "reachable": True,
                    "protocol_version": "0.1.0",
                    "last_seen": int(time.time()),
                }
            )
        return peers

    async def invoke_skill(skill_name: str, payload: dict[str, Any] | None = None) -> Any:
        if skill_name not in skill_registry:
            raise KeyError(f"unknown skill: {skill_name}")
        add_log("info", f"Executing skill {skill_name}", skill=skill_name)
        return skill_registry.call(skill_name, payload or {})

    @app.get("/api/v1/health")
    async def health() -> dict[str, Any]:
        add_log("info", "Health probe", status="ok")
        return {
            "status": "ok",
            "gateway": "IMesh",
            "timestamp": int(time.time()),
            "models": [model["id"] for model in _default_models()],
        }

    @app.post("/api/v1/checkout/free-key")
    async def free_key() -> dict[str, str]:
        api_key = f"imesh_{secrets.token_urlsafe(24)}"
        db.add_key(api_key)
        add_log("info", "Issued API key", api_key_prefix=api_key[:8])
        return {"api_key": api_key}

    @app.get("/api/v1/skills")
    async def get_skills() -> dict[str, Any]:
        return {"skills": [tool["name"] for tool in skill_registry.describe_tools()]}

    @app.get("/api/v1/peers")
    async def get_peers() -> dict[str, Any]:
        add_log("info", "Requested peer list")
        return {"peers": collect_peers()}

    @app.post("/api/v1/execute")
    async def execute(request: Request) -> dict[str, Any]:
        body = await request.json()
        skill = body.get("skill", "echo")
        payload = body.get("payload", {}) if isinstance(body.get("payload", {}), dict) else {}
        try:
            result = await invoke_skill(skill, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"unknown skill: {skill}") from exc
        return {
            "status": "ok",
            "skill": skill,
            "payload": payload,
            "result": result,
        }

    @app.post("/api/v1/test-skill")
    async def test_skill(request: Request) -> dict[str, Any]:
        body = await request.json()
        skill = body.get("skill", "echo")
        payload = body.get("payload", {}) if isinstance(body.get("payload", {}), dict) else {}
        try:
            result = await invoke_skill(skill, payload)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"unknown skill: {skill}") from exc
        return {"skill": skill, "payload": payload, "result": result}

    @app.post("/v1/chat/completions")
    async def openai_chat(request: Request) -> dict[str, Any]:
        body = await request.json()
        messages = body.get("messages", []) or []
        prompt = _extract_last_user_message(messages)
        model = body.get("model") or "openclaw-mesh"

        skill_name = body.get("skill") or _infer_skill_from_prompt(prompt, skill_registry)
        if skill_name is None:
            skill_name = "echo"

        try:
            result = await invoke_skill(skill_name, {"messages": messages, "prompt": prompt})
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"unknown skill: {skill_name}") from exc

        content = _stringify_result(result)
        return {
            "id": f"chatcmpl-{int(time.time() * 1000)}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": len(prompt.split()),
                "completion_tokens": len(content.split()),
                "total_tokens": len(prompt.split()) + len(content.split()),
            },
        }

    @app.post("/v1/messages")
    async def anthropic_messages(request: Request) -> dict[str, Any]:
        body = await request.json()
        messages = body.get("messages", []) or []
        prompt = _extract_last_user_message(messages)
        model = body.get("model") or "openclaw-mesh"
        skill_name = body.get("skill") or _infer_skill_from_prompt(prompt, skill_registry)
        if skill_name is None:
            skill_name = "echo"

        try:
            result = await invoke_skill(skill_name, {"messages": messages, "prompt": prompt})
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=f"unknown skill: {skill_name}") from exc

        content = _stringify_result(result)
        return {
            "id": f"msg-{int(time.time() * 1000)}",
            "type": "message",
            "role": "assistant",
            "model": model,
            "content": [{"type": "text", "text": content}],
        }

    @app.get("/api/v1/models")
    async def models() -> dict[str, Any]:
        add_log("info", "Requested model list")
        return _model_listing()

    @app.get("/api/v1/portal-data")
    async def portal_data() -> dict[str, Any]:
        add_log("info", "Portal data requested")
        peers = collect_peers()
        models = _default_models()
        logs = app.state.logs[-50:]
        return {
            "models": models,
            "peers": peers,
            "diagnostics": {
                "gateway_host": settings.gateway_host,
                "gateway_port": settings.gateway_port,
                "mdns_enabled": settings.mdns_enabled,
                "wan_enabled": settings.wan_enabled,
                "dht_enabled": settings.dht_enabled,
                "quic_enabled": settings.quic_enabled,
                "gossipsub_enabled": settings.gossipsub_enabled,
                "skills_available": sorted(skill_registry._skills.keys()),
                "peer_ttl_seconds": getattr(app.state.discovery, "peer_ttl_seconds", 120),
            },
            "logs": logs,
            "summary": _portal_summary(models, peers, logs),
        }

    @app.get("/", response_class=HTMLResponse)
    async def portal() -> HTMLResponse:
        return HTMLResponse(
            content="""
            <html>
              <head>
                <meta charset=\"UTF-8\" />
                <title>IMesh Portal</title>
                <style>
                  :root {
                    --bg: #020817;
                    --panel: rgba(15, 23, 42, 0.8);
                    --panel-soft: rgba(30, 41, 59, 0.7);
                    --border: #334155;
                    --text: #e2e8f0;
                    --muted: #94a3b8;
                    --green: #22c55e;
                    --amber: #f59e0b;
                    --red: #ef4444;
                    --blue: #60a5fa;
                  }
                  * { box-sizing: border-box; }
                  body {
                    margin: 0;
                    background: linear-gradient(135deg, #020817, #0f172a 40%, #111827);
                    color: var(--text);
                    font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
                  }
                  .container { max-width: 1280px; margin: 0 auto; padding: 2rem 1rem 3rem; }
                  .topbar {
                    display: flex; justify-content: space-between; align-items: center;
                    gap: 1rem; margin-bottom: 1.5rem;
                  }
                  .title {
                    font-size: 2rem; font-weight: 800; margin: 0;
                  }
                  .subtitle { color: var(--muted); margin-top: 0.25rem; }
                  .header-actions { display: flex; gap: 0.75rem; }
                  button {
                    border: 1px solid var(--border);
                    background: rgba(96, 165, 250, 0.14);
                    color: var(--text);
                    border-radius: 10px;
                    padding: 0.7rem 1rem;
                    font-weight: 700;
                    cursor: pointer;
                  }
                  button.primary { background: linear-gradient(135deg, #22c55e, #16a34a); color: #052e16; border: none; }
                  .cards {
                    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                    gap: 1rem; margin-bottom: 1.5rem;
                  }
                  .card {
                    background: var(--panel);
                    border: 1px solid var(--border);
                    border-radius: 14px;
                    padding: 1rem;
                    box-shadow: 0 10px 30px rgba(15, 23, 42, 0.35);
                  }
                  .card-label { color: var(--muted); font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.08em; }
                  .card-value { font-size: 1.8rem; font-weight: 800; margin-top: 0.35rem; }
                  .grid { display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 1rem; }
                  .panel {
                    background: var(--panel);
                    border: 1px solid var(--border);
                    border-radius: 14px;
                    padding: 1rem;
                    overflow: hidden;
                  }
                  .panel h2 { margin-top: 0; margin-bottom: 0.8rem; }
                  .panel-header {
                    display: flex; justify-content: space-between; align-items: center; gap: 0.75rem;
                    margin-bottom: 0.75rem;
                  }
                  .peer-toolbar {
                    display: grid; grid-template-columns: repeat(3, minmax(160px, 1fr));
                    gap: 0.75rem; margin-bottom: 0.8rem;
                  }
                  .log-toolbar {
                    display: grid; grid-template-columns: repeat(2, minmax(160px, 1fr));
                    gap: 0.75rem; margin-bottom: 0.8rem;
                  }
                  .small-button {
                    padding: 0.5rem 0.75rem; font-size: 0.85rem; border-radius: 8px;
                  }
                  table { width: 100%; border-collapse: collapse; }
                  th, td { border-bottom: 1px solid var(--border); padding: 0.55rem 0.3rem; text-align: left; }
                  th { color: var(--muted); font-size: 0.8rem; text-transform: uppercase; }
                  .status-badge {
                    display: inline-flex; align-items: center; padding: 0.2rem 0.5rem; border-radius: 999px;
                    font-size: 0.75rem; font-weight: 700;
                  }
                  .status-badge.up { background: rgba(34, 197, 94, 0.12); color: #86efac; }
                  .status-badge.down { background: rgba(239, 68, 68, 0.12); color: #fca5a5; }
                  .stack {
                    display: grid; gap: 1rem;
                  }
                  pre {
                    margin: 0;
                    background: rgba(2, 6, 23, 0.85);
                    border: 1px solid var(--border);
                    border-radius: 10px;
                    padding: 0.75rem;
                    overflow: auto;
                    white-space: pre-wrap;
                    word-break: break-word;
                    color: #dbeafe;
                  }
                  label { display: block; margin-top: 0.8rem; color: var(--muted); }
                  input, textarea, select {
                    width: 100%; box-sizing: border-box; margin-top: 0.4rem;
                    background: rgba(15, 23, 42, 0.8);
                    border: 1px solid var(--border);
                    border-radius: 10px;
                    padding: 0.7rem 0.8rem;
                    color: var(--text);
                  }
                  textarea { min-height: 120px; resize: vertical; }
                  .actions { display: flex; gap: 0.75rem; margin-top: 0.75rem; }
                  .muted { color: var(--muted); }
                  .message {
                    margin-top: 0.8rem; border-radius: 10px; padding: 0.75rem; border: 1px solid var(--border);
                    background: rgba(15, 23, 42, 0.8);
                    display: none;
                  }
                  .message.show { display: block; }
                  .message.error { border-color: rgba(239, 68, 68, 0.7); color: #fecaca; }
                  .message.ok { border-color: rgba(34, 197, 94, 0.7); color: #bbf7d0; }
                  @media (max-width: 900px) { .grid { grid-template-columns: 1fr; } }
                </style>
              </head>
              <body>
                <div class=\"container\">
                  <div class=\"topbar\">
                    <div>
                      <h1 class=\"title\">IMesh Portal</h1>
                      <div class=\"subtitle\">Production-ready mesh dashboard</div>
                    </div>
                    <div class=\"header-actions\">
                      <button id=\"refresh-button\">Refresh</button>
                    </div>
                  </div>

                  <div class=\"cards\">
                    <div class=\"card\">
                      <div class=\"card-label\">Peers</div>
                      <div class=\"card-value\" id=\"summary-peers\">0</div>
                    </div>
                    <div class=\"card\">
                      <div class=\"card-label\">Reachable</div>
                      <div class=\"card-value\" id=\"summary-reachable\">0</div>
                    </div>
                    <div class=\"card\">
                      <div class=\"card-label\">Models</div>
                      <div class=\"card-value\" id=\"summary-models\">0</div>
                    </div>
                    <div class=\"card\">
                      <div class=\"card-label\">Skills</div>
                      <div class=\"card-value\" id=\"summary-skills\">0</div>
                    </div>
                  </div>

                  <div class=\"grid\">
                    <div class=\"panel\">
                      <div class=\"panel-header\">
                        <h2>Peers</h2>
                      </div>
                      <div class=\"peer-toolbar\">
                        <input id=\"peer-search\" type=\"text\" placeholder=\"Search peers...\" />
                        <select id=\"peer-status-filter\">
                          <option value=\"all\">All statuses</option>
                          <option value=\"reachable\">Reachable</option>
                          <option value=\"down\">Down</option>
                        </select>
                        <select id=\"peer-skill-filter\">
                          <option value=\"all\">All skills</option>
                        </select>
                      </div>
                      <table>
                        <thead>
                          <tr>
                            <th>Name</th>
                            <th>Host</th>
                            <th>Port</th>
                            <th>Status</th>
                            <th>Skills</th>
                          </tr>
                        </thead>
                        <tbody id=\"peers-body\"></tbody>
                      </table>
                    </div>

                    <div class=\"stack\">
                      <div class=\"panel\">
                        <div class=\"panel-header\">
                          <h2>Diagnostics</h2>
                          <button id=\"export-diagnostics\" class=\"small-button\">Export JSON</button>
                        </div>
                        <pre id=\"diagnostics\"></pre>
                      </div>
                      <div class=\"panel\">
                        <div class=\"panel-header\">
                          <h2>Recent logs</h2>
                          <button id=\"export-logs\" class=\"small-button\">Export JSON</button>
                        </div>
                        <div class=\"log-toolbar\">
                          <input id=\"log-search\" type=\"text\" placeholder=\"Search logs by text or field...\" />
                          <select id=\"log-level-filter\">
                            <option value=\"all\">All levels</option>
                            <option value=\"info\">Info</option>
                            <option value=\"warning\">Warning</option>
                            <option value=\"error\">Error</option>
                          </select>
                        </div>
                        <pre id=\"logs\"></pre>
                      </div>
                    </div>
                  </div>

                  <div class=\"panel\" style=\"margin-top: 1rem;\">
                    <h2>Manual skill test</h2>
                    <label>Skill
                      <select id=\"skill-select\"></select>
                    </label>
                    <label>Payload JSON
                      <textarea id=\"payload\" rows=\"6\">{}</textarea>
                    </label>
                    <div class=\"actions\">
                      <button id=\"run-test\" class=\"primary\">Run skill</button>
                    </div>
                    <div id=\"skill-message\" class=\"message\"></div>
                    <pre id=\"skill-result\" class=\"muted\">No test run yet.</pre>
                  </div>
                </div>

                <script>
                  const peersBody = document.getElementById('peers-body');
                  const diagnosticsEl = document.getElementById('diagnostics');
                  const logsEl = document.getElementById('logs');
                  const skillSelect = document.getElementById('skill-select');
                  const payloadEl = document.getElementById('payload');
                  const skillResult = document.getElementById('skill-result');
                  const skillMessage = document.getElementById('skill-message');
                  const refreshButton = document.getElementById('refresh-button');
                  const peerSearch = document.getElementById('peer-search');
                  const peerStatusFilter = document.getElementById('peer-status-filter');
                  const peerSkillFilter = document.getElementById('peer-skill-filter');
                  const logSearch = document.getElementById('log-search');
                  const logLevelFilter = document.getElementById('log-level-filter');
                  const exportDiagnosticsButton = document.getElementById('export-diagnostics');
                  const exportLogsButton = document.getElementById('export-logs');

                  let portalData = { peers: [], diagnostics: {}, logs: [], summary: {} };

                  function downloadJson(filename, data) {
                    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = filename;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    URL.revokeObjectURL(url);
                  }

                  function setMessage(text, kind = 'ok') {
                    skillMessage.textContent = text;
                    skillMessage.className = 'message show ' + kind;
                  }

                  function setSummary(data) {
                    const summary = data.summary || {};
                    document.getElementById('summary-peers').textContent = summary.peers_count || 0;
                    document.getElementById('summary-reachable').textContent = summary.reachable_peers || 0;
                    document.getElementById('summary-models').textContent = summary.models_count || 0;
                    document.getElementById('summary-skills').textContent = summary.skills_count || 0;
                  }

                  function applyPeerFilters() {
                    const search = (peerSearch.value || '').trim().toLowerCase();
                    const status = peerStatusFilter.value;
                    const skill = peerSkillFilter.value;

                    return (portalData.peers || []).filter(peer => {
                      const matchesSearch = !search ||
                        [peer.name, peer.host, peer.port, (peer.skills || []).join(' ')].join(' ').toLowerCase().includes(search);

                      const matchesStatus = status === 'all' ||
                        (status === 'reachable' && peer.reachable) ||
                        (status === 'down' && !peer.reachable);

                      const matchesSkill = skill === 'all' || (peer.skills || []).includes(skill);

                      return matchesSearch && matchesStatus && matchesSkill;
                    });
                  }

                  function applyLogFilters() {
                    const search = (logSearch.value || '').trim().toLowerCase();
                    const level = logLevelFilter.value;

                    return (portalData.logs || []).filter(log => {
                      const haystack = [
                        log.message,
                        log.level,
                        log.skill,
                        log.api_key_prefix,
                        log.status,
                        String(log.timestamp || '')
                      ].filter(Boolean).join(' ').toLowerCase();

                      const matchesSearch = !search || haystack.includes(search);
                      const matchesLevel = level === 'all' || log.level === level;

                      return matchesSearch && matchesLevel;
                    });
                  }

                  function renderPeers(peers) {
                    peersBody.innerHTML = peers.map(peer => `
                      <tr>
                        <td>${peer.name}</td>
                        <td>${peer.host}</td>
                        <td>${peer.port}</td>
                        <td>
                          <span class=\"status-badge ${peer.reachable ? 'up' : 'down'}\">
                            ${peer.reachable ? 'Reachable' : 'Down'}
                          </span>
                        </td>
                        <td>${(peer.skills || []).join(', ') || '—'}</td>
                      </tr>
                    `).join('');
                  }

                  function renderLogs() {
                    const filteredLogs = applyLogFilters();
                    logsEl.textContent = JSON.stringify(filteredLogs, null, 2) || 'No log entries match the current filters.';
                  }

                  async function loadPortalData() {
                    try {
                      const response = await fetch('/api/v1/portal-data');
                      if (!response.ok) {
                        throw new Error('Unable to load portal data');
                      }

                      portalData = await response.json();
                      renderPeers(applyPeerFilters());
                      diagnosticsEl.textContent = JSON.stringify(portalData.diagnostics, null, 2);
                      renderLogs();
                      setSummary(portalData);

                      const skillOptions = Array.from(new Set((portalData.peers || []).flatMap(peer => peer.skills || [])));
                      const currentSkillValue = peerSkillFilter.value;
                      peerSkillFilter.innerHTML = '<option value=\"all\">All skills</option>' + skillOptions.map(skill => `<option value=\"${skill}\">${skill}</option>`).join('');
                      if (skillOptions.includes(currentSkillValue)) {
                        peerSkillFilter.value = currentSkillValue;
                      }

                      const skillOptionsForSelection = Array.from(new Set(portalData.diagnostics.skills_available || []));
                      if (skillOptionsForSelection.length) {
                        skillSelect.innerHTML = skillOptionsForSelection.map(skill => `<option value=\"${skill}\">${skill}</option>`).join('');
                      }
                    } catch (error) {
                      setMessage('Portal refresh failed: ' + error.message, 'error');
                    }
                  }

                  document.getElementById('run-test').addEventListener('click', async () => {
                    try {
                      const payload = JSON.parse(payloadEl.value || '{}');
                      const response = await fetch('/api/v1/test-skill', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ skill: skillSelect.value, payload })
                      });

                      if (!response.ok) {
                        const errorPayload = await response.json();
                        throw new Error(errorPayload.detail || 'Skill execution failed');
                      }

                      const result = await response.json();
                      skillResult.textContent = JSON.stringify(result, null, 2);
                      setMessage('Skill executed successfully.', 'ok');
                    } catch (error) {
                      skillResult.textContent = error.message;
                      setMessage('Skill execution failed: ' + error.message, 'error');
                    }
                  });

                  refreshButton.addEventListener('click', loadPortalData);
                  peerSearch.addEventListener('input', () => renderPeers(applyPeerFilters()));
                  peerStatusFilter.addEventListener('change', () => renderPeers(applyPeerFilters()));
                  peerSkillFilter.addEventListener('change', () => renderPeers(applyPeerFilters()));
                  logSearch.addEventListener('input', renderLogs);
                  logLevelFilter.addEventListener('change', renderLogs);
                  exportDiagnosticsButton.addEventListener('click', () => downloadJson('diagnostics.json', portalData.diagnostics));
                  exportLogsButton.addEventListener('click', () => downloadJson('logs.json', applyLogFilters()));

                  loadPortalData();
                  setInterval(loadPortalData, 5000);
                </script>
              </body>
            </html>
            """,
            status_code=200,
        )

    return app
