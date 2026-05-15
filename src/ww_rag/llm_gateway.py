from __future__ import annotations

from ww_rag.models import SourceRef


class ModelGateway:
    """Model abstraction for IBM/watsonx/third-party LLM integrations.

    The default implementation is extractive and offline so the first version
    can run in a private environment without sending source text to a provider.
    Replace this class with a watsonx or approved third-party adapter later.
    """

    def answer(self, question: str, citations: list[SourceRef], min_score: float) -> str:
        if not citations or citations[0].score < min_score:
            return "No clear evidence was found in the indexed project materials."
        lines = [
            "Based on the indexed project materials, the relevant evidence is:",
        ]
        for index, citation in enumerate(citations[:4], start=1):
            lines.append(f"{index}. {citation.text_preview.strip()}")
            lines.append(f"   Source: {citation.file_name}, {citation.location}")
        lines.append("Use the cited sources as the authority. If sources conflict, prefer documents marked current or the most recently updated files.")
        return "\n".join(lines)


