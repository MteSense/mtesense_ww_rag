from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True)
class SourceRef:
    document_id: str
    chunk_id: str
    file_name: str
    relative_path: str
    location: str
    score: float
    text_preview: str


@dataclass
class ParsedSection:
    text: str
    location: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class QueryResult:
    answer_id: str
    answer: str
    confidence: float
    citations: list[SourceRef]
    trace_id: str

