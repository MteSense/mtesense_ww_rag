from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ww_rag.config import Settings
from ww_rag.service import RagService


class SyncAndQueryTests(unittest.TestCase):
    def test_sync_indexes_text_and_query_returns_citation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "docs"
            root.mkdir()
            (root / "alert process final.txt").write_text(
                "Final conclusion: the alert escalation process is L1 checks impact first, then escalates to L2 if not restored in 15 minutes.",
                encoding="utf-8",
            )
            settings = _settings(root, Path(temp) / "rag.sqlite3")
            service = RagService(settings)
            try:
                stats = service.sync_local()
                self.assertEqual(stats["indexed"], 1)
                result = service.query({"question": "What is the alert escalation process?"})
                self.assertGreater(result.confidence, 0)
                self.assertTrue(result.citations)
                self.assertIn("alert process final.txt", result.citations[0].file_name)
            finally:
                service.close()

    def test_sync_marks_duplicate_and_deleted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "docs"
            root.mkdir()
            first = root / "a.txt"
            second = root / "b.txt"
            first.write_text("same content", encoding="utf-8")
            second.write_text("same content", encoding="utf-8")
            settings = _settings(root, Path(temp) / "rag.sqlite3")
            service = RagService(settings)
            try:
                service.sync_local()
                docs = service.documents()
                self.assertEqual(len(docs), 2)
                self.assertIn("duplicate", {doc["status"] for doc in docs})
                second.unlink()
                stats = service.sync_local()
                self.assertEqual(stats["deleted"], 1)
            finally:
                service.close()

    def test_patch_document_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "docs"
            root.mkdir()
            (root / "draft.txt").write_text("draft requirement", encoding="utf-8")
            settings = _settings(root, Path(temp) / "rag.sqlite3")
            service = RagService(settings)
            try:
                service.sync_local()
                document = service.documents()[0]
                updated = service.patch_document(document["id"], {"status": "current", "metadata": {"business_domain": ["alerting"]}})
                self.assertEqual(updated["status"], "current")
                self.assertEqual(updated["metadata"]["business_domain"], ["alerting"])
            finally:
                service.close()


def _settings(source: Path, storage: Path) -> Settings:
    base = Settings.from_env()
    return Settings(
        source_dir=source,
        project_id="test",
        storage_path=storage,
        scan_interval=base.scan_interval,
        exclude_patterns=base.exclude_patterns,
        allowed_extensions=base.allowed_extensions,
        top_k=base.top_k,
        min_score=0.01,
    )


if __name__ == "__main__":
    unittest.main()


