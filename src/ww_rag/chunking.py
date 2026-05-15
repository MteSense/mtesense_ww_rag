from __future__ import annotations

from ww_rag.models import ParsedSection


def chunk_sections(sections: list[ParsedSection], max_chars: int = 1200, overlap: int = 160) -> list[ParsedSection]:
    chunks: list[ParsedSection] = []
    for section in sections:
        text = " ".join(section.text.split())
        if not text:
            continue
        if len(text) <= max_chars:
            chunks.append(section)
            continue
        start = 0
        part = 1
        while start < len(text):
            end = min(start + max_chars, len(text))
            split = _best_split(text, start, end)
            chunk_text = text[start:split].strip()
            if chunk_text:
                metadata = dict(section.metadata)
                metadata["chunk_part"] = part
                chunks.append(ParsedSection(text=chunk_text, location=f"{section.location} part {part}", metadata=metadata))
            if split >= len(text):
                break
            start = max(0, split - overlap)
            part += 1
    return chunks


def _best_split(text: str, start: int, end: int) -> int:
    if end >= len(text):
        return len(text)
    window = text[start:end]
    for marker in ("\n\n", "。", ".", ";", "；", "\n", " "):
        index = window.rfind(marker)
        if index > max(50, len(window) // 2):
            return start + index + len(marker)
    return end


