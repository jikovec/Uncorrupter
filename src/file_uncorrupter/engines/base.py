from __future__ import annotations

from abc import ABC, abstractmethod

from ..types import Candidate, Classification, FileRecord


class RecoveryEngine(ABC):
    name: str
    families: tuple[str, ...]

    @abstractmethod
    def generate_candidates(self, record: FileRecord, data: bytes, classification: Classification) -> list[Candidate]:
        raise NotImplementedError
