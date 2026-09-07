from __future__ import annotations

import platform
from dataclasses import dataclass, field
from enum import Enum


class HardwareBackend(str, Enum):
    CPU = "cpu"
    CUDA = "cuda"
    ROCM = "rocm"
    OPENVINO = "openvino"
    MLX = "mlx"


@dataclass(slots=True)
class HardwareStatus:
    backend: HardwareBackend
    available: bool
    details: dict[str, object] = field(default_factory=dict)


class HardwareDetector:
    """Detect local AI hardware with explicit fallback behavior."""

    @staticmethod
    def detect() -> HardwareStatus:
        system = platform.system().lower()
        machine = platform.machine().lower()
        details: dict[str, object] = {"system": system, "machine": machine}

        try:
            import torch  # type: ignore

            if torch.cuda.is_available():
                return HardwareStatus(HardwareBackend.CUDA, True, {**details, "cuda_devices": torch.cuda.device_count()})
        except Exception:  # pragma: no cover - optional dependency may be absent
            pass

        try:
            import torch  # type: ignore

            if hasattr(torch, "rocm") and torch.version.hip is not None:  # type: ignore[attr-defined]
                return HardwareStatus(HardwareBackend.ROCM, True, details)
        except Exception:  # pragma: no cover
            pass

        try:
            import openvino  # type: ignore

            return HardwareStatus(HardwareBackend.OPENVINO, True, details)
        except Exception:  # pragma: no cover
            pass

        try:
            import mlx.core  # type: ignore

            return HardwareStatus(HardwareBackend.MLX, True, details)
        except Exception:  # pragma: no cover
            pass

        return HardwareStatus(HardwareBackend.CPU, True, details)


def detect_hardware() -> HardwareStatus:
    return HardwareDetector.detect()
