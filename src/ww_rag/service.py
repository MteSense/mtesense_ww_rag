from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ww_rag.config import Settings
from ww_rag.llm_gateway import ModelGateway
from ww_rag.models import QueryResult
from ww_rag.retrieval import Retriever
from ww_rag.scanner import sync_local
from ww_rag.storage import Storage
from ww_rag.text import stable_hash


class RagService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.storage = Storage(settings.storage_path)
        self.retriever = Retriever(self.storage)
        self.model_gateway = ModelGateway()

    def close(self) -> None:
        self.storage.close()

    def sync_local(self, source: str | None = None) -> dict[str, Any]:
        settings = self.settings.with_source(source)
        return sync_local(settings, self.storage)

    def query(self, payload: dict[str, Any]) -> QueryResult:
        question = str(payload.get("question", "")).strip()
        if not question:
            raise ValueError("question is required")
        project_id = str(payload.get("project_id") or self.settings.project_id)
        top_k = int(payload.get("top_k") or self.settings.top_k)
        citations = self.retriever.search(project_id, question, top_k=top_k)
        confidence = citations[0].score if citations else 0.0
        answer = self.model_gateway.answer(question, citations, self.settings.min_score)
        answer_id = stable_hash(f"{project_id}:{question}:{','.join(item.chunk_id for item in citations)}")[:24]
        trace_id = stable_hash(f"trace:{answer_id}:{len(citations)}")[:24]
        citation_dicts = [asdict(item) for item in citations]
        self.storage.save_answer(answer_id, project_id, question, answer, citation_dicts, confidence)
        return QueryResult(answer_id=answer_id, answer=answer, confidence=confidence, citations=citations, trace_id=trace_id)

    def sources(self, answer_id: str) -> dict[str, Any] | None:
        answer = self.storage.get_answer(answer_id)
        if answer is None:
            return None
        return {"answer_id": answer_id, "citations": answer["citations"]}

    def feedback(self, payload: dict[str, Any]) -> dict[str, Any]:
        rating = str(payload.get("rating", "")).strip()
        if not rating:
            raise ValueError("rating is required")
        feedback_id = stable_hash(f"feedback:{payload.get('answer_id')}:{rating}:{payload.get('comment', '')}")[:24]
        self.storage.save_feedback(feedback_id, payload.get("answer_id"), rating, payload.get("comment"))
        return {"id": feedback_id, "status": "accepted"}

    def documents(self, project_id: str | None = None) -> list[dict[str, Any]]:
        return self.storage.list_documents(project_id or self.settings.project_id)

    def patch_document(self, document_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.storage.update_document(document_id, payload)


