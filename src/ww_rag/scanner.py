from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any

from ww_rag.chunking import chunk_sections
from ww_rag.config import Settings
from ww_rag.metadata import classify_document
from ww_rag.parsers import parse_file
from ww_rag.storage import Storage
from ww_rag.text import file_sha256, stable_hash, text_vector, tokenize


def sync_local(settings: Settings, storage: Storage) -> dict[str, Any]:
    source_dir = settings.validate_source()
    seen: set[str] = set()
    stats = {
        "project_id": settings.project_id,
        "source_dir": str(source_dir),
        "scanned": 0,
        "indexed": 0,
        "unchanged": 0,
        "skipped": 0,
        "deleted": 0,
        "errors": [],
    }
    hash_to_document: dict[str, str] = {}

    for path in source_dir.rglob("*"):
        if not path.is_file():
            continue
        rel_path = path.relative_to(source_dir).as_posix()
        if _excluded(rel_path, settings.exclude_patterns) or path.suffix.lower() not in settings.allowed_extensions:
            stats["skipped"] += 1
            continue
        seen.add(rel_path)
        stats["scanned"] += 1
        try:
            changed = _index_file(settings, storage, source_dir, path, rel_path, hash_to_document)
            if changed:
                stats["indexed"] += 1
            else:
                stats["unchanged"] += 1
        except Exception as exc:
            stats["errors"].append({"file": rel_path, "error": str(exc)})
    stats["deleted"] = storage.mark_missing_deleted(settings.project_id, seen)
    return stats


def _index_file(settings: Settings, storage: Storage, source_dir: Path, path: Path, rel_path: str, hash_to_document: dict[str, str]) -> bool:
    stat = path.stat()
    content_hash = file_sha256(path)
    sections = parse_file(path)
    sample = "\n".join(section.text for section in sections[:5])
    metadata = classify_document(path.relative_to(source_dir), sample)
    status = metadata.pop("document_status")
    if content_hash in hash_to_document:
        status = "duplicate"
        metadata["duplicate_of"] = hash_to_document[content_hash]
    document_id = stable_hash(f"{settings.project_id}:{rel_path}")
    document = {
        "id": document_id,
        "project_id": settings.project_id,
        "relative_path": rel_path,
        "file_name": path.name,
        "extension": path.suffix.lower(),
        "size": stat.st_size,
        "content_hash": content_hash,
        "modified_at": _mtime_iso(stat.st_mtime),
        "status": status,
        "process_status": "parsed",
        "metadata": metadata,
    }
    changed = storage.upsert_document(document)
    if not changed:
        return False
    hash_to_document.setdefault(content_hash, rel_path)
    chunks = []
    for index, section in enumerate(chunk_sections(sections), start=1):
        chunk_text = section.text.strip()
        if not chunk_text:
            continue
        chunk_metadata = dict(metadata)
        chunk_metadata.update(section.metadata)
        chunk_metadata["document_status"] = status
        chunks.append(
            {
                "id": stable_hash(f"{document_id}:{index}:{chunk_text[:64]}"),
                "document_id": document_id,
                "project_id": settings.project_id,
                "chunk_index": index,
                "text": chunk_text,
                "location": section.location,
                "metadata": chunk_metadata,
                "tokens": tokenize(f"{path.name} {section.location} {chunk_text}"),
                "vector": text_vector(chunk_text),
            }
        )
    storage.replace_chunks(document_id, chunks)
    return True


def _excluded(relative_path: str, patterns: tuple[str, ...]) -> bool:
    value = relative_path.replace("\\", "/")
    return any(fnmatch.fnmatch(value, pattern) or fnmatch.fnmatch(Path(value).name, pattern) for pattern in patterns)


def _mtime_iso(timestamp: float) -> str:
    from datetime import datetime, timezone

    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec="seconds")


