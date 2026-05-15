from __future__ import annotations

import re
from pathlib import Path
from typing import Any


DOCUMENT_TYPE_RULES = {
    "requirement": ("requirement", "requirements", "brd", "prd", "story", "user story", "rtvm"),
    "design": ("design", "architecture", "solution", "hld", "lld", "interface", "api"),
    "meeting": ("meeting", "minutes", "mom", "recording"),
    "runbook": ("operation", "runbook", "manual", "sop", "guide", "playbook"),
    "issue": ("issue", "defect", "bug", "incident", "open item", "risk"),
    "report": ("report", "status", "weekly", "monthly"),
}

PHASE_RULES = {
    "presales": ("presales", "proposal", "rfp", "quote"),
    "design": ("design", "architecture", "solution"),
    "development": ("development", "dev", "implementation"),
    "testing": ("testing", "sit", "uat", "test"),
    "go_live": ("go live", "golive", "go-live", "cutover"),
    "operations": ("operations", "ops", "operation", "support"),
}

BUSINESS_RULES = {
    "alerting": ("alert", "alarm", "event"),
    "monitoring": ("monitor", "monitoring", "observability"),
    "asset": ("asset", "cmdb"),
    "permission": ("permission", "role", "access"),
    "reporting": ("report", "dashboard"),
    "order": ("order",),
    "billing": ("billing", "invoice"),
    "storage": ("storage", "fusion", "ceph", "odf"),
    "architecture": ("architecture", "hld", "lld"),
}


def classify_document(path: Path, text_sample: str) -> dict[str, Any]:
    haystack = f"{path.name} {path.parent} {text_sample[:4000]}".lower()
    tags: dict[str, Any] = {
        "project_phase": _first_match(haystack, PHASE_RULES) or "unknown",
        "business_domain": _all_matches(haystack, BUSINESS_RULES),
        "document_type": _first_match(haystack, DOCUMENT_TYPE_RULES) or _type_from_extension(path),
        "related_systems": _systems(haystack),
        "related_teams": _teams(haystack),
        "version": _version(path.name),
        "has_final_conclusion": _has_final_conclusion(haystack),
    }
    tags["document_status"] = infer_status(path, haystack)
    return tags


def infer_status(path: Path, haystack: str) -> str:
    name = path.name.lower()
    if any(marker in name for marker in ("draft", "wip", "working")):
        return "draft"
    if any(marker in name for marker in ("old", "archive", "obsolete", "deprecated")):
        return "outdated"
    if path.suffix.lower() in {".tmp", ".bak"} or name.startswith("~$"):
        return "unknown"
    if any(marker in haystack for marker in ("final", "approved", "baseline")):
        return "current"
    return "unknown"


def _first_match(text: str, rules: dict[str, tuple[str, ...]]) -> str | None:
    for label, needles in rules.items():
        if any(needle.lower() in text for needle in needles):
            return label
    return None


def _all_matches(text: str, rules: dict[str, tuple[str, ...]]) -> list[str]:
    return [label for label, needles in rules.items() if any(needle.lower() in text for needle in needles)]


def _type_from_extension(path: Path) -> str:
    if path.suffix.lower() in {".mp4", ".mov", ".m4a"}:
        return "meeting"
    if path.suffix.lower() == ".xlsx":
        return "spreadsheet"
    if path.suffix.lower() == ".pptx":
        return "presentation"
    return "document"


def _version(name: str) -> str | None:
    match = re.search(r"\b[vV](\d+(?:\.\d+)*)\b", name)
    if match:
        return match.group(0)
    match = re.search(r"\b(\d{4}[-_.]?\d{2}[-_.]?\d{2})\b", name)
    return match.group(1) if match else None


def _has_final_conclusion(text: str) -> bool:
    return any(marker in text for marker in ("final decision", "conclusion", "approved", "decision"))


def _systems(text: str) -> list[str]:
    candidates = set(re.findall(r"\b[A-Z][A-Z0-9_-]{2,}\b", text.upper()))
    return sorted(item for item in candidates if item not in {"PDF", "DOCX", "PPTX", "XLSX", "TXT"})


def _teams(text: str) -> list[str]:
    matches = re.findall(r"\b([a-z0-9_-]+ team|team [a-z0-9_-]+)\b", text.lower())
    return sorted(set(matches))
