# AGENTS.md

## Project Overview

This repository contains `ww-rag`, a local-folder Retrieval-Augmented Generation (RAG) service for project documents.

The service scans a configured local document directory, parses supported files, stores document/chunk metadata in SQLite, and exposes a FastAPI API that can be used by Slack bots, CLI users, or future web applications.

The project is currently a lightweight PoC-style RAG implementation. It does not call an external LLM by default. The default answer generation is extractive and offline through `ModelGateway`.

## Important Data Boundary

Do not commit or upload indexed project data.

Ignored local artifacts include:

- `.rag/`
- `.rag/rag.sqlite3`
- `.pytest_cache/`
- `__pycache__/`
- `.venv/`
- build outputs

The real project documents are expected to live outside this repository and are referenced through `RAG_SOURCE_DIR`.

## Main Runtime Configuration

Environment variables:

- `RAGPYTHONPATH`: path to this repository's Python source directory, usually `src`.
- `RAG_SOURCE_DIR`: required local document source directory for sync.
- `RAG_PROJECT_ID`: project identifier used to scope documents and queries.
- `RAG_STORAGE_PATH`: SQLite database path, default `.rag/rag.sqlite3`.
- `RAG_SCAN_INTERVAL`: scheduler interval label, default `daily`.
- `RAG_EXCLUDE_PATTERNS`: comma-separated exclude rules.
- `RAG_ALLOWED_EXTENSIONS`: comma-separated file extension allowlist.
- `RAG_TOP_K`: retrieval result count, default `8`.
- `RAG_MIN_SCORE`: minimum evidence score, default `0.12`.

Use `run_ww_rag.py` as the launcher. It reads `RAGPYTHONPATH` and adds it to `sys.path` before importing `ww_rag`.

## Common Commands

Windows PowerShell:

```powershell
python -m pip install -e .
$env:RAGPYTHONPATH="$PWD\src"
$env:RAG_SOURCE_DIR="document path"
$env:RAG_PROJECT_ID="project name"
python run_ww_rag.py sync
python run_ww_rag.py serve --host 127.0.0.1 --port 8080
```

Linux/macOS:

```bash
python -m pip install -e .
export RAGPYTHONPATH="$PWD/src"
export RAG_SOURCE_DIR="document path"
export RAG_PROJECT_ID="project name"
python run_ww_rag.py sync
python run_ww_rag.py serve --host 127.0.0.1 --port 8080
```

Run tests:

```bash
python -m pytest -v
```

If pytest cannot import the package directly, set `PYTHONPATH=src` for tests or install the package with `python -m pip install -e .`.

## API

The API is implemented with FastAPI in `src/ww_rag/api.py`.

Important endpoints:

- `GET /health`
- `POST /api/v1/query`
- `POST /api/v1/sync/local`
- `GET /api/v1/sources/{answer_id}`
- `POST /api/v1/feedback`
- `GET /api/v1/documents`
- `PATCH /api/v1/documents/{document_id}`

FastAPI docs are available at:

```text
http://127.0.0.1:8080/docs
```

## Architecture Notes

Core modules:

- `config.py`: environment-based settings.
- `scanner.py`: local folder sync, hashing, duplicate detection, changed-file detection, soft deletion.
- `parsers.py`: file parsing for text, Markdown, DOCX, PPTX, XLSX, PDF, draw.io, MSG placeholder, and sidecar transcripts for video/audio.
- `chunking.py`: chunk splitting with overlap.
- `metadata.py`: rule-based document metadata classification.
- `storage.py`: SQLite schema and persistence.
- `retrieval.py`: lightweight hybrid retrieval.
- `llm_gateway.py`: offline/extractive answer generation placeholder for future IBM/watsonx/third-party LLM integrations.
- `service.py`: orchestration layer used by CLI, API, and Slack adapter.
- `scheduler.py`: optional in-process sync scheduler.
- `slack_adapter.py`: skeleton adapter for Slack bot integration.

## Sync Behavior

`sync_local` scans `RAG_SOURCE_DIR` recursively.

Behavior:

- New files are parsed, chunked, and indexed.
- Modified files are detected by `content_hash` and `modified_at`; old chunks are replaced.
- Duplicate content is marked with document status `duplicate`.
- Missing files are soft-deleted by setting `deleted_at` and `process_status='deleted'`.
- Soft-deleted documents are excluded from retrieval.
- Unchanged files are not re-parsed.

Starting the API does not automatically sync unless requested:

- Use `--sync-on-start` to sync immediately at startup.
- Use `--enable-scheduler` to enable the in-process scheduler.
- `RAG_SCAN_INTERVAL=daily` means once every 24 hours.

## Retrieval Behavior

Current retrieval is local and lightweight:

- Token overlap lexical score.
- Hashed vector cosine similarity.
- Metadata boost.
- Document status weighting.
- Basic source/location deduplication.

Status weights:

- `current`: highest boost.
- `unknown`: neutral.
- `draft`, `outdated`, and `duplicate`: lower weights.

This is intentionally simple. For production-quality retrieval, consider adding:

- Real embedding model.
- FAISS, Qdrant, or Milvus.
- Reranker.
- Query expansion.
- Version-aware document grouping.
- Evaluation set with expected citations.

## Parser Notes

Supported extensions by default:

- `.txt`
- `.md`
- `.docx`
- `.pptx`
- `.xlsx`
- `.pdf`
- `.drawio`
- `.msg`
- `.mp4`
- `.mov`
- `.m4a`

Important details:

- `.msg` is not fully parsed; it is indexed with a placeholder asking users to export the email as `.txt`, `.html`, or `.pdf`.
- Video/audio files are indexed through same-stem transcript sidecars: `.txt`, `.vtt`, or `.srt`.
- DOCX and XLSX have fallback ZIP/XML parsers if optional parser dependencies are unavailable.
- PDF parsing requires `pypdf`; without it the document gets a parser-unavailable placeholder.

## Model Behavior

The current default model layer does not call an external model.

`ModelGateway.answer` returns an evidence-oriented answer from retrieved chunks. It should be replaced or extended when integrating IBM models, watsonx, or approved third-party LLMs.

Keep the LLM boundary narrow: send only top-k retrieved snippets, not full source files.

## Tests

Tests live in `tests/` and currently cover:

- Settings validation.
- Local sync and query behavior.
- Duplicate and deleted-file handling.
- Document patching.
- FastAPI route creation and service-backed endpoint behavior.

Run:

```bash
python -m pytest -v
```

## Repository

Current remote:

```text
https://github.com/MteSense/mtesense_ww_rag.git
```

License:

```text
MIT
```

## Development Guidance

- Keep source code under `src/ww_rag`.
- Keep tests under `tests`.
- Do not commit real document folders, generated SQLite databases, or cache folders.
- Preserve the FastAPI API contract unless intentionally changing clients.
- Prefer small, focused changes with tests.
- Keep README examples generic; do not hard-code private customer/project paths.
- Avoid adding external LLM calls directly into retrieval or API handlers; route them through `llm_gateway.py`.
