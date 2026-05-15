from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ww_rag.config import Settings


class ConfigTests(unittest.TestCase):
    def test_validate_source_requires_path(self) -> None:
        settings = Settings.from_env()
        settings = Settings(
            source_dir=None,
            project_id=settings.project_id,
            storage_path=settings.storage_path,
            scan_interval=settings.scan_interval,
            exclude_patterns=settings.exclude_patterns,
            allowed_extensions=settings.allowed_extensions,
            top_k=settings.top_k,
            min_score=settings.min_score,
        )
        with self.assertRaises(ValueError):
            settings.validate_source()

    def test_validate_source_accepts_space_path(self) -> None:
        with tempfile.TemporaryDirectory(prefix="data library ") as temp:
            settings = Settings.from_env().with_source(temp)
            self.assertEqual(settings.validate_source(), Path(temp).resolve())


if __name__ == "__main__":
    unittest.main()


