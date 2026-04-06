from __future__ import annotations

from .jpeg_v1 import JPEGRecoveryEngineV1
from .media_v2 import BaselineRecoveryEngineV2


def build_registry() -> dict[str, object]:
    jpeg_v1 = JPEGRecoveryEngineV1()
    baseline_v2 = BaselineRecoveryEngineV2()
    return {
        jpeg_v1.name: jpeg_v1,
        baseline_v2.name: baseline_v2,
    }
