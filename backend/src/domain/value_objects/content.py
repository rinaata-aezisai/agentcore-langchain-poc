"""Content Value Object"""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class ContentType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"


@dataclass(frozen=True)
class Content:
    text: str
    type: ContentType = ContentType.TEXT
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_text(cls, text: str) -> "Content":
        if not text or not text.strip():
            raise EmptyContentError()
        return cls(text=text, type=ContentType.TEXT)

    def truncate(self, max_length: int) -> "Content":
        if len(self.text) <= max_length:
            return self
        return Content(text=self.text[:max_length] + "...", type=self.type, metadata=self.metadata)


class EmptyContentError(Exception):
    def __init__(self):
        super().__init__("Content cannot be empty")



