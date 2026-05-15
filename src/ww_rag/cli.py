from __future__ import annotations

import argparse
import json
import os
import sys

from ww_rag.config import Settings
from ww_rag.scheduler import SyncScheduler
from ww_rag.service import RagService


def main(argv: list[str] | None = None) -> int:
    _configure_stdout()
    parser = argparse.ArgumentParser(prog="ww-rag")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync_parser = subparsers.add_parser("sync", help="scan and index RAG_SOURCE_DIR")
    sync_parser.add_argument("--source", help="override RAG_SOURCE_DIR")

    query_parser = subparsers.add_parser("query", help="query the local RAG index")
    query_parser.add_argument("question")
    query_parser.add_argument("--project-id")
    query_parser.add_argument("--top-k", type=int)

    serve_parser = subparsers.add_parser("serve", help="start the HTTP API")
    serve_parser.add_argument("--host", default="127.0.0.1")
    serve_parser.add_argument("--port", type=int, default=8080)
    serve_parser.add_argument("--sync-on-start", action="store_true")
    serve_parser.add_argument("--enable-scheduler", action="store_true")

    args = parser.parse_args(argv)
    _ensure_src_on_path()
    settings = Settings.from_env()

    if args.command == "sync":
        service = RagService(settings)
        try:
            print(json.dumps(service.sync_local(args.source), ensure_ascii=False, indent=2))
            return 0
        finally:
            service.close()

    if args.command == "query":
        service = RagService(settings)
        try:
            payload = {"question": args.question}
            if args.project_id:
                payload["project_id"] = args.project_id
            if args.top_k:
                payload["top_k"] = args.top_k
            result = service.query(payload)
            print(result.answer)
            print(json.dumps([citation.__dict__ for citation in result.citations], ensure_ascii=False, indent=2))
            return 0
        finally:
            service.close()

    if args.command == "serve":
        return _serve_fastapi(settings, args.host, args.port, args.sync_on_start, args.enable_scheduler)

    return 1


def _ensure_src_on_path() -> None:
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    if root not in sys.path:
        sys.path.insert(0, root)


def _configure_stdout() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def _serve_fastapi(settings: Settings, host: str, port: int, sync_on_start: bool, enable_scheduler: bool) -> int:
    try:
        import uvicorn
        from ww_rag.api import create_app
    except ModuleNotFoundError as exc:
        raise SystemExit(
            "FastAPI runtime dependencies are missing. Install them with: "
            "python -m pip install fastapi uvicorn pydantic"
        ) from exc

    service = RagService(settings)
    scheduler = None
    if sync_on_start:
        service.sync_local()
    if enable_scheduler:
        scheduler = SyncScheduler(service, settings.scan_interval)
        scheduler.start()
    app = create_app(settings=settings, service=service)
    print(f"Serving WW RAG FastAPI on http://{host}:{port}")
    try:
        uvicorn.run(app, host=host, port=port)
        return 0
    finally:
        if scheduler:
            scheduler.stop()


if __name__ == "__main__":
    raise SystemExit(main())

