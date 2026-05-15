from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from ww_rag.config import Settings
from ww_rag.service import RagService


class QueryRequest(BaseModel):
    user: str | None = None
    question: str = Field(..., min_length=1)
    project_id: str | None = None
    conversation_id: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=50)


class SyncRequest(BaseModel):
    source_dir: str | None = None


class FeedbackRequest(BaseModel):
    answer_id: str | None = None
    rating: str = Field(..., min_length=1)
    comment: str | None = None


class DocumentPatchRequest(BaseModel):
    status: str | None = None
    metadata: dict[str, Any] | None = None


def create_app(settings: Settings | None = None, service: RagService | None = None) -> FastAPI:
    app_settings = settings or Settings.from_env()
    rag_service = service or RagService(app_settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        try:
            yield
        finally:
            app.state.rag_service.close()

    app = FastAPI(
        title="WW RAG API",
        version="0.1.0",
        description="Local-folder RAG API for project documents.",
        lifespan=lifespan,
    )
    app.state.rag_service = rag_service

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/v1/query")
    def query(payload: QueryRequest) -> dict[str, Any]:
        try:
            result = app.state.rag_service.query(payload.model_dump(exclude_none=True))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        return {
            "answer_id": result.answer_id,
            "answer": result.answer,
            "confidence": result.confidence,
            "trace_id": result.trace_id,
            "citations": [asdict(citation) for citation in result.citations],
        }

    @app.post("/api/v1/sync/local")
    def sync_local(payload: SyncRequest | None = None) -> dict[str, Any]:
        body = payload or SyncRequest()
        try:
            return app.state.rag_service.sync_local(body.source_dir)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @app.get("/api/v1/sources/{answer_id}")
    def sources(answer_id: str) -> dict[str, Any]:
        result = app.state.rag_service.sources(answer_id)
        if result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="answer not found")
        return result

    @app.post("/api/v1/feedback", status_code=status.HTTP_202_ACCEPTED)
    def feedback(payload: FeedbackRequest) -> dict[str, Any]:
        try:
            return app.state.rag_service.feedback(payload.model_dump(exclude_none=True))
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    @app.get("/api/v1/documents")
    def documents(project_id: str | None = Query(default=None)) -> dict[str, Any]:
        return {"documents": app.state.rag_service.documents(project_id)}

    @app.patch("/api/v1/documents/{document_id}")
    def patch_document(document_id: str, payload: DocumentPatchRequest) -> dict[str, Any]:
        try:
            return app.state.rag_service.patch_document(document_id, payload.model_dump(exclude_none=True))
        except KeyError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="document not found") from exc

    return app


app = create_app()
