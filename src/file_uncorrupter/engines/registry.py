from __future__ import annotations

from .jpeg_v1 import JPEGRecoveryEngineV1


def build_registry() -> dict[str, object]:
    jpeg_v1 = JPEGRecoveryEngineV1()
    return {
        jpeg_v1.name: jpeg_v1,
    }
