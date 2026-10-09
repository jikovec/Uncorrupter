from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from .base import CapabilityRecord, FormatHandler


class HandlerRegistry:
    def __init__(self, handlers: Iterable[FormatHandler] = ()) -> None:
        self._handlers: dict[str, FormatHandler] = {}
        self._families: dict[str, list[FormatHandler]] = defaultdict(list)
        for handler in handlers:
            self.register(handler)

    def register(self, handler: FormatHandler) -> None:
        if handler.handler_id in self._handlers:
            raise ValueError(f"duplicate handler id: {handler.handler_id}")
        capabilities = handler.capabilities()
        if not capabilities:
            raise ValueError(f"handler has no capabilities: {handler.handler_id}")
        self._handlers[handler.handler_id] = handler
        for capability in capabilities:
            if capability.handler_id and capability.handler_id != handler.handler_id:
                raise ValueError(f"capability handler mismatch for {capability.family}")
            self._families[capability.family].append(handler)
            for variant in capability.variants:
                if handler not in self._families[variant]:
                    self._families[variant].append(handler)
        for family in self._families:
            self._families[family].sort(key=lambda item: item.handler_id)

    def get(self, handler_id: str) -> FormatHandler:
        return self._handlers[handler_id]

    def for_family(self, family: str) -> tuple[FormatHandler, ...]:
        return tuple(self._families.get(family, ()))

    def handlers(self) -> tuple[FormatHandler, ...]:
        return tuple(self._handlers[key] for key in sorted(self._handlers))

    def capabilities(self) -> list[CapabilityRecord]:
        records = [record for handler in self.handlers() for record in handler.capabilities()]
        return sorted(records, key=lambda record: (record.family, record.handler_id, record.variants))

    def manifest(self) -> dict[str, object]:
        return {"schema_version": 1, "capabilities": [record.to_dict() for record in self.capabilities()]}


def build_handler_registry(*, include_optional: bool = True) -> HandlerRegistry:
    from .legacy_media import LegacyMediaHandler

    handlers: list[FormatHandler] = [LegacyMediaHandler()]
    if include_optional:
        for module_name, class_name in (
            ("text", "TextHandler"),
            ("archive", "ArchiveHandler"),
            ("package_document", "PackageDocumentHandler"),
            ("pdf", "PDFHandler"),
            ("image", "ImageHandler"),
            ("media", "MediaHandler"),
            ("external", "ExternalAdapterHandler"),
        ):
            try:
                module = __import__(f"file_uncorrupter.handlers.{module_name}", fromlist=[class_name])
            except ImportError:
                continue
            handlers.append(getattr(module, class_name)())
    return HandlerRegistry(handlers)
