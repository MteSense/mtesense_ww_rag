from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    rag_python_path = os.getenv("RAGPYTHONPATH")
    if rag_python_path:
        for raw_path in rag_python_path.split(os.pathsep):
            path = raw_path.strip()
            if path:
                sys.path.insert(0, str(Path(path).expanduser().resolve()))
    else:
        sys.path.insert(0, str((Path(__file__).resolve().parent / "src").resolve()))

    from ww_rag.cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
