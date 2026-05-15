from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ww_rag.service import RagService


class SlackRagAdapter:
    """Small adapter so Slack handlers can share the same RAG API behavior.

    A production Slack Bolt app can call `handle_question` from an app mention,
    slash command, or message shortcut handler.
    """

    def __init__(self, service: RagService):
        self.service = service

    def handle_question(self, user_id: str, question: str, channel_id: str | None = None, thread_ts: str | None = None) -> dict[str, Any]:
        result = self.service.query(
            {
                "user": user_id,
                "question": question,
                "conversation_id": thread_ts or channel_id,
            }
        )
        blocks = [
            {"type": "section", "text": {"type": "mrkdwn", "text": result.answer}},
        ]
        if result.citations:
            citations = "\n".join(
                f"- `{citation.file_name}` `{citation.location}` score={citation.score}"
                for citation in result.citations[:5]
            )
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": f"*Sources*\n{citations}"}})
        return {
            "text": result.answer,
            "answer_id": result.answer_id,
            "trace_id": result.trace_id,
            "confidence": result.confidence,
            "citations": [asdict(citation) for citation in result.citations],
            "blocks": blocks,
        }


