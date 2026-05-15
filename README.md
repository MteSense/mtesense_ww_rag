# WW RAG

Local-folder RAG service for project documents. The source folder is configured with `RAG_SOURCE_DIR`; the service scans files recursively, parses supported document formats, builds a local SQLite index, and exposes query APIs that can be reused by a Slack bot or a future web application.

## Features

- Local sync with new, changed, duplicate, and missing-file detection.
- Document governance labels: `current`, `outdated`, `draft`, `duplicate`, `unknown`.
- Parsers for `.txt`, `.md`, `.docx`, `.pptx`, `.xlsx`, `.pdf`, and `.drawio`.
- Video/audio files can be indexed through sidecar transcripts with the same file stem: `.txt`, `.vtt`, or `.srt`.
- `.msg` files are recorded with a reminder to export them as `.txt`, `.html`, or `.pdf` for full indexing.
- Lightweight hybrid retrieval: keyword overlap, hashed vector similarity, metadata/status weighting, and rerank.
- HTTP API for sync, query, source lookup, feedback, document list, and document metadata correction.
- FastAPI runtime with generated OpenAPI docs at `/docs`.
- Slack adapter skeleton that calls the same query service.

## Quick Start

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
$env:RAGPYTHONPATH="$PWD\src"
$env:RAG_SOURCE_DIR="document path"
$env:RAG_PROJECT_ID="project name"
python run_ww_rag.py sync
python run_ww_rag.py serve --host 127.0.0.1 --port 8080
```

### Linux/macOS

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
export RAGPYTHONPATH="$PWD/src"
export RAG_SOURCE_DIR="document path"
export RAG_PROJECT_ID="project name"
python run_ww_rag.py sync
python run_ww_rag.py serve --host 127.0.0.1 --port 8080
```

If you already have an activated Python environment, skip the virtual environment setup and run the environment variable commands plus the `python run_ww_rag.py ...` commands for your shell.

`RAGPYTHONPATH` points to this repository's Python source directory. The launcher reads it and adds it to Python's import path before loading `ww_rag`.

## Query from the CLI

### Windows PowerShell

```powershell
$env:RAGPYTHONPATH="$PWD\src"
$env:RAG_PROJECT_ID="project name"
python run_ww_rag.py query "project question" --project-id "project name" --top-k 3
```

### Linux/macOS

```bash
export RAGPYTHONPATH="$PWD/src"
export RAG_PROJECT_ID="project name"
python run_ww_rag.py query "project question" --project-id "project name" --top-k 3
```

## API Examples

After starting the API, open the generated FastAPI docs:

```text
http://127.0.0.1:8080/docs
```

Sync local files:

```http
POST /api/v1/sync/local
Content-Type: application/json

{}
```

Query:

```http
POST /api/v1/query
Content-Type: application/json

{
  "user": "u123",
  "question": "project question",
  "project_id": "project name",
  "conversation_id": "slack-thread-1"
}
```

Documents:

```http
GET /api/v1/documents
```

Feedback:

```http
POST /api/v1/feedback
Content-Type: application/json

{
  "answer_id": "answer-id",
  "rating": "not_helpful",
  "comment": "The citation is not accurate."
}
```

## Configuration

- `RAG_SOURCE_DIR`: required local source folder.
- `RAG_PROJECT_ID`: project identifier, default `default`.
- `RAG_STORAGE_PATH`: SQLite path, default `.rag/rag.sqlite3`.
- `RAG_SCAN_INTERVAL`: scheduler interval label, default `daily`.
- `RAG_EXCLUDE_PATTERNS`: comma-separated exclude rules.
- `RAG_ALLOWED_EXTENSIONS`: comma-separated allowed file extensions.
- `RAG_TOP_K`: retrieval candidate count, default `8`.
- `RAG_MIN_SCORE`: minimum evidence score, default `0.12`.

## Notes

Version 1 uses project-level access control. It controls who can use the RAG service, but it does not perform per-file ACL filtering on each query.
