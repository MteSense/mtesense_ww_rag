from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ww_rag.api import create_app
from ww_rag.config import Settings
from ww_rag.service import RagService


class ApiHandlerTests(unittest.TestCase):
    def test_service_backed_endpoints_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "docs"
            root.mkdir()
            (root / "runbook.txt").write_text("Monitoring runbook: check the dashboard first for CPU alerts.", encoding="utf-8")
            service = RagService(_settings(root, Path(temp) / "rag.sqlite3"))
            try:
                sync = service.sync_local()
                query = service.query({"question": "What should be checked first for CPU alerts?"})
                sources = service.sources(query.answer_id)
                feedback = service.feedback({"answer_id": query.answer_id, "rating": "helpful"})
                self.assertEqual(sync["indexed"], 1)
                self.assertIsNotNone(sources)
                self.assertEqual(feedback["status"], "accepted")
                app = create_app(settings=_settings(root, Path(temp) / "api.sqlite3"))
                try:
                    routes = {route.path for route in app.routes}
                    self.assertIn("/api/v1/query", routes)
                finally:
                    app.state.rag_service.close()
                json.dumps(feedback)
            finally:
                service.close()


def _settings(source: Path, storage: Path) -> Settings:
    base = Settings.from_env()
    return Settings(
        source_dir=source,
        project_id="api",
        storage_path=storage,
        scan_interval=base.scan_interval,
        exclude_patterns=base.exclude_patterns,
        allowed_extensions=base.allowed_extensions,
        top_k=base.top_k,
        min_score=0.01,
    )


if __name__ == "__main__":
    unittest.main()


