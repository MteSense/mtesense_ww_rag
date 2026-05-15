from __future__ import annotations

from collections import Counter
from typing import Any

from ww_rag.models import SourceRef
from ww_rag.text import cosine, text_vector, tokenize


STATUS_WEIGHT = {
    "current": 1.2,
    "unknown": 1.0,
    "draft": 0.75,
    "outdated": 0.55,
    "duplicate": 0.35,
}


class Retriever:
    def __init__(self, storage):
        self.storage = storage

    def search(self, project_id: str, question: str, top_k: int = 8) -> list[SourceRef]:
        chunks = self.storage.list_chunks(project_id)
        if not chunks:
            return []
        query_tokens = tokenize(question)
        query_counts = Counter(query_tokens)
        query_vector = text_vector(question)
        scored: list[tuple[float, dict[str, Any]]] = []
        for chunk in chunks:
            lexical = _lexical_score(query_counts, Counter(chunk["tokens"]))
            semantic = cosine(query_vector, chunk["vector"])
            metadata_boost = _metadata_boost(question, chunk["metadata"])
            status_weight = STATUS_WEIGHT.get(chunk["document_status"], 1.0)
            score = ((0.62 * lexical) + (0.33 * semantic) + metadata_boost) * status_weight
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        deduped: list[SourceRef] = []
        seen_docs: set[str] = set()
        for score, chunk in scored:
            if len(deduped) >= top_k:
                break
            doc_key = f"{chunk['relative_path']}:{chunk['location']}"
            if doc_key in seen_docs:
                continue
            seen_docs.add(doc_key)
            deduped.append(
                SourceRef(
                    document_id=chunk["document_id"],
                    chunk_id=chunk["id"],
                    file_name=chunk["file_name"],
                    relative_path=chunk["relative_path"],
                    location=chunk["location"],
                    score=round(float(score), 4),
                    text_preview=chunk["text"][:500],
                )
            )
        return deduped


def _lexical_score(query: Counter[str], document: Counter[str]) -> float:
    if not query or not document:
        return 0.0
    overlap = sum(min(count, document.get(token, 0)) for token, count in query.items())
    return overlap / max(1, sum(query.values()))


def _metadata_boost(question: str, metadata: dict[str, Any]) -> float:
    text = question.lower()
    boost = 0.0
    for value in metadata.values():
        if isinstance(value, str) and value and value.lower() in text:
            boost += 0.02
        elif isinstance(value, list):
            boost += sum(0.015 for item in value if isinstance(item, str) and item.lower() in text)
    return min(boost, 0.08)


