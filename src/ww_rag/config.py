from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ALLOWED_EXTENSIONS = (
    ".txt",
    ".md",
    ".docx",
    ".pptx",
    ".xlsx",
    ".pdf",
    ".drawio",
    ".msg",
    ".mp4",
    ".mov",
    ".m4a",
)

DEFAULT_EXCLUDE_PATTERNS = (
    "~$*",
    "*.tmp",
    "*.bak",
    "archive/**",
    "temp/**",
    "tmp/**",
    ".git/**",
    "__pycache__/**",
)


def _split_csv(value: str | None, default: tuple[str, ...]) -> tuple[str, ...]:
    if not value:
        return default
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    source_dir: Path | None
    project_id: str
    storage_path: Path
    scan_interval: str
    exclude_patterns: tuple[str, ...]
    allowed_extensions: tuple[str, ...]
    top_k: int
    min_score: float

    @classmethod
    def from_env(cls) -> "Settings":
        source = os.getenv("RAG_SOURCE_DIR")
        storage = os.getenv("RAG_STORAGE_PATH", ".rag/rag.sqlite3")
        return cls(
            source_dir=Path(source).expanduser().resolve() if source else None,
            project_id=os.getenv("RAG_PROJECT_ID", "default"),
            storage_path=Path(storage).expanduser(),
            scan_interval=os.getenv("RAG_SCAN_INTERVAL", "daily"),
            exclude_patterns=_split_csv(os.getenv("RAG_EXCLUDE_PATTERNS"), DEFAULT_EXCLUDE_PATTERNS),
            allowed_extensions=tuple(ext.lower() for ext in _split_csv(os.getenv("RAG_ALLOWED_EXTENSIONS"), DEFAULT_ALLOWED_EXTENSIONS)),
            top_k=int(os.getenv("RAG_TOP_K", "8")),
            min_score=float(os.getenv("RAG_MIN_SCORE", "0.12")),
        )

    def with_source(self, source: str | None) -> "Settings":
        if not source:
            return self
        return Settings(
            source_dir=Path(source).expanduser().resolve(),
            project_id=self.project_id,
            storage_path=self.storage_path,
            scan_interval=self.scan_interval,
            exclude_patterns=self.exclude_patterns,
            allowed_extensions=self.allowed_extensions,
            top_k=self.top_k,
            min_score=self.min_score,
        )

    def validate_source(self) -> Path:
        if self.source_dir is None:
            raise ValueError("RAG_SOURCE_DIR is required for local sync")
        if not self.source_dir.exists():
            raise ValueError(f"RAG_SOURCE_DIR does not exist: {self.source_dir}")
        if not self.source_dir.is_dir():
            raise ValueError(f"RAG_SOURCE_DIR is not a directory: {self.source_dir}")
        return self.source_dir
