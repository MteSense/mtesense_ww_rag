from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from ww_rag.models import utc_now_iso


class Storage:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path), timeout=30, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.init_schema()

    def close(self) -> None:
        self.conn.close()

    def init_schema(self) -> None:
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                file_name TEXT NOT NULL,
                extension TEXT NOT NULL,
                size INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                modified_at TEXT NOT NULL,
                status TEXT NOT NULL,
                process_status TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                indexed_at TEXT,
                deleted_at TEXT,
                UNIQUE(project_id, relative_path)
            );

            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                project_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                text TEXT NOT NULL,
                location TEXT NOT NULL,
                metadata_json TEXT NOT NULL,
                token_json TEXT NOT NULL,
                vector_json TEXT NOT NULL,
                FOREIGN KEY(document_id) REFERENCES documents(id)
            );

            CREATE TABLE IF NOT EXISTS answers (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                citations_json TEXT NOT NULL,
                confidence REAL NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                answer_id TEXT,
                rating TEXT NOT NULL,
                comment TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        self.conn.commit()

    def upsert_document(self, document: dict[str, Any]) -> bool:
        existing = self.get_document_by_path(document["project_id"], document["relative_path"])
        changed = existing is None or existing["content_hash"] != document["content_hash"] or existing["modified_at"] != document["modified_at"]
        self.conn.execute(
            """
            INSERT INTO documents (
                id, project_id, relative_path, file_name, extension, size, content_hash,
                modified_at, status, process_status, metadata_json, indexed_at, deleted_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
            ON CONFLICT(project_id, relative_path) DO UPDATE SET
                file_name=excluded.file_name,
                extension=excluded.extension,
                size=excluded.size,
                content_hash=excluded.content_hash,
                modified_at=excluded.modified_at,
                status=excluded.status,
                process_status=excluded.process_status,
                metadata_json=excluded.metadata_json,
                deleted_at=NULL
            """,
            (
                document["id"],
                document["project_id"],
                document["relative_path"],
                document["file_name"],
                document["extension"],
                document["size"],
                document["content_hash"],
                document["modified_at"],
                document["status"],
                document["process_status"],
                json.dumps(document["metadata"], ensure_ascii=False),
                document.get("indexed_at"),
            ),
        )
        self.conn.commit()
        return changed

    def get_document_by_path(self, project_id: str, relative_path: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM documents WHERE project_id = ? AND relative_path = ?",
            (project_id, relative_path),
        ).fetchone()

    def get_document(self, document_id: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()

    def mark_missing_deleted(self, project_id: str, seen_relative_paths: set[str]) -> int:
        rows = self.conn.execute(
            "SELECT relative_path FROM documents WHERE project_id = ? AND deleted_at IS NULL",
            (project_id,),
        ).fetchall()
        deleted = 0
        for row in rows:
            if row["relative_path"] not in seen_relative_paths:
                self.conn.execute(
                    "UPDATE documents SET deleted_at = ?, process_status = 'deleted' WHERE project_id = ? AND relative_path = ?",
                    (utc_now_iso(), project_id, row["relative_path"]),
                )
                deleted += 1
        self.conn.commit()
        return deleted

    def replace_chunks(self, document_id: str, chunks: list[dict[str, Any]]) -> None:
        self.conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
        self.conn.executemany(
            """
            INSERT INTO chunks (
                id, document_id, project_id, chunk_index, text, location,
                metadata_json, token_json, vector_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    chunk["id"],
                    chunk["document_id"],
                    chunk["project_id"],
                    chunk["chunk_index"],
                    chunk["text"],
                    chunk["location"],
                    json.dumps(chunk["metadata"], ensure_ascii=False),
                    json.dumps(chunk["tokens"], ensure_ascii=False),
                    json.dumps(chunk["vector"]),
                )
                for chunk in chunks
            ],
        )
        self.conn.execute(
            "UPDATE documents SET indexed_at = ?, process_status = 'indexed' WHERE id = ?",
            (utc_now_iso(), document_id),
        )
        self.conn.commit()

    def list_documents(self, project_id: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM documents"
        params: tuple[Any, ...] = ()
        if project_id:
            query += " WHERE project_id = ?"
            params = (project_id,)
        query += " ORDER BY relative_path"
        return [self._document_to_dict(row) for row in self.conn.execute(query, params).fetchall()]

    def list_chunks(self, project_id: str) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            """
            SELECT chunks.*, documents.file_name, documents.relative_path, documents.status AS document_status,
                   documents.deleted_at
            FROM chunks
            JOIN documents ON documents.id = chunks.document_id
            WHERE chunks.project_id = ? AND documents.deleted_at IS NULL
            """,
            (project_id,),
        ).fetchall()
        return [self._chunk_to_dict(row) for row in rows]

    def update_document(self, document_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        document = self.get_document(document_id)
        if document is None:
            raise KeyError(document_id)
        metadata = json.loads(document["metadata_json"])
        if "metadata" in patch and isinstance(patch["metadata"], dict):
            metadata.update(patch["metadata"])
        status = patch.get("status", document["status"])
        self.conn.execute(
            "UPDATE documents SET status = ?, metadata_json = ? WHERE id = ?",
            (status, json.dumps(metadata, ensure_ascii=False), document_id),
        )
        self.conn.commit()
        updated = self.get_document(document_id)
        if updated is None:
            raise KeyError(document_id)
        return self._document_to_dict(updated)

    def save_answer(self, answer_id: str, project_id: str, question: str, answer: str, citations: list[dict[str, Any]], confidence: float) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO answers (id, project_id, question, answer, citations_json, confidence, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (answer_id, project_id, question, answer, json.dumps(citations, ensure_ascii=False), confidence, utc_now_iso()),
        )
        self.conn.commit()

    def get_answer(self, answer_id: str) -> dict[str, Any] | None:
        row = self.conn.execute("SELECT * FROM answers WHERE id = ?", (answer_id,)).fetchone()
        if row is None:
            return None
        return {
            "id": row["id"],
            "project_id": row["project_id"],
            "question": row["question"],
            "answer": row["answer"],
            "citations": json.loads(row["citations_json"]),
            "confidence": row["confidence"],
            "created_at": row["created_at"],
        }

    def save_feedback(self, feedback_id: str, answer_id: str | None, rating: str, comment: str | None) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO feedback (id, answer_id, rating, comment, created_at) VALUES (?, ?, ?, ?, ?)",
            (feedback_id, answer_id, rating, comment, utc_now_iso()),
        )
        self.conn.commit()

    def _document_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "project_id": row["project_id"],
            "relative_path": row["relative_path"],
            "file_name": row["file_name"],
            "extension": row["extension"],
            "size": row["size"],
            "content_hash": row["content_hash"],
            "modified_at": row["modified_at"],
            "status": row["status"],
            "process_status": row["process_status"],
            "metadata": json.loads(row["metadata_json"]),
            "indexed_at": row["indexed_at"],
            "deleted_at": row["deleted_at"],
        }

    def _chunk_to_dict(self, row: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": row["id"],
            "document_id": row["document_id"],
            "project_id": row["project_id"],
            "chunk_index": row["chunk_index"],
            "text": row["text"],
            "location": row["location"],
            "metadata": json.loads(row["metadata_json"]),
            "tokens": json.loads(row["token_json"]),
            "vector": json.loads(row["vector_json"]),
            "file_name": row["file_name"],
            "relative_path": row["relative_path"],
            "document_status": row["document_status"],
            "deleted_at": row["deleted_at"],
        }

