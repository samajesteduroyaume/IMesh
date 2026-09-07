from __future__ import annotations

from typing import Any

from .hardware import detect_hardware


class UniversalInferenceEngine:
    def __init__(self, model_name: str | None = None, device: str | None = None, quantization: str | None = None) -> None:
        self.model_name = model_name or "fallback-model"
        self.device = device or detect_hardware().backend.value
        self.quantization = quantization or "fp16"
        self.ready = True

    def generate(self, prompt: str, max_tokens: int = 32, stream: bool = False) -> dict[str, Any]:
        text = f"[{self.device}] stub response for: {prompt}"
        if stream:
            return {"stream": [text[:i] for i in range(1, min(len(text), max_tokens) + 1)]}
        return {"text": text[:max_tokens], "device": self.device, "model": self.model_name}

    async def generate_async(self, prompt: str, max_tokens: int = 32) -> dict[str, Any]:
        return self.generate(prompt, max_tokens=max_tokens)
