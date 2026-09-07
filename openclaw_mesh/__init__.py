"""Public package API for IMesh."""

from .client import MeshClient
from .config import Settings, get_settings, reload_settings, reset_settings
from .discovery import MeshDiscovery, PeerInfo
from .node import IMeshNode, MeshServer
from .protocol import TaskChunk, TaskRequest, TaskResponse, parse_message
from .registry import SkillRegistry, skill

__all__ = [
    "IMeshNode",
    "MeshClient",
    "MeshDiscovery",
    "MeshServer",
    "PeerInfo",
    "Settings",
    "SkillRegistry",
    "TaskChunk",
    "TaskRequest",
    "TaskResponse",
    "get_settings",
    "parse_message",
    "reload_settings",
    "reset_settings",
    "skill",
]
