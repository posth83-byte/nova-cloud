"""Guarded exact-text patch helpers for SYSTEM_ENGINEER's GitHub delivery path."""

from __future__ import annotations

from typing import Iterable


def select_independent_review_provider(generation_engine: str, gemini_available: bool, openrouter_available: bool):
    """Choose a different provider for code review; never silently self-review."""
    engine = str(generation_engine or "").strip().lower()
    if engine.startswith("gemini"):
        return "OpenRouter" if openrouter_available else None
    if engine.startswith("openrouter"):
        return "Gemini" if gemini_available else None
    return None


def build_source_excerpt(source: str, max_chars: int = 28000) -> str:
    """Return bounded, line-numbered source windows around the JARVIS execution pipeline."""
    lines = str(source or "").splitlines()
    markers = (
        ("async def jarvis_job_worker_loop", 245),
        ('@app.post("/api/jarvis/jobs")', 115),
        ('@app.post("/api/jarvis/delegate")', 145),
        ("SYSTEM_ENGINEER_PROMPT =", 115),
        ('@app.get("/api/status")', 100),
    )
    windows = []
    for marker, size in markers:
        for index, line in enumerate(lines):
            if marker in line:
                windows.append((max(0, index - 10), min(len(lines), index + size)))
                break
    merged = []
    for start, end in sorted(windows):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    chunks = []
    for start, end in merged:
        chunks.append("\n".join(f"{number + 1}: {lines[number]}" for number in range(start, end)))
    excerpt = "\n\n[VERIFIED SOURCE WINDOW]\n\n".join(chunks)
    return excerpt[:max_chars]


def normalize_patch_spec(spec):
    """Normalize common model patch-list aliases without weakening patch validation."""
    if isinstance(spec, list):
        return {"summary": "Patchlista returnerad som rotlista.", "changes": spec}
    if not isinstance(spec, dict):
        raise ValueError("SYSTEM_ENGINEER-svaret måste vara ett JSON-objekt med changes-lista.")
    normalized = dict(spec)
    changes = normalized.get("changes")
    if not isinstance(changes, list):
        for alias in ("patches", "edits", "patch_list", "operations"):
            candidate = normalized.get(alias)
            if isinstance(candidate, list):
                normalized["changes"] = candidate
                break
    if not isinstance(normalized.get("changes"), list):
        raise ValueError(
            "SYSTEM_ENGINEER-svaret saknar en giltig changes-lista. "
            "Returnera changes som en lista med 1–4 patchobjekt, eller [] endast vid verklig no-op."
        )
    return normalized


def apply_exact_text_patches(source: str, changes: Iterable[dict], allowed_paths=("main.py",)):
    """Apply only bounded, exact, unique text replacements to explicitly allowed files."""
    if not isinstance(changes, list) or not 1 <= len(changes) <= 4:
        raise ValueError("Patchlistan måste innehålla 1–4 ändringar.")
    updated = str(source)
    applied = []
    for item in changes:
        if not isinstance(item, dict):
            raise ValueError("Varje patch måste vara ett objekt.")
        path = str(item.get("path") or "")
        if path not in allowed_paths:
            raise ValueError(f"Otillåten filväg: {path or '(tom)'}")
        old_text = str(item.get("old_text") or "")
        new_text = str(item.get("new_text") or "")
        if not old_text or not new_text:
            raise ValueError("Patchen måste innehålla både old_text och new_text.")
        if len(old_text) > 6000 or len(new_text) > 10000:
            raise ValueError("Patchen överskrider storleksgränsen.")
        occurrences = updated.count(old_text)
        if occurrences != 1:
            raise ValueError(
                f"old_text måste förekomma exakt en gång; hittade {occurrences} förekomster."
            )
        updated = updated.replace(old_text, new_text, 1)
        applied.append({"path": path, "old_text": old_text, "new_text": new_text})
    if len(updated.encode("utf-8")) > 400000:
        raise ValueError("Den uppdaterade filen överskrider 400 KB.")
    return updated, applied


def is_verified_noop_review(review: dict) -> bool:
    """Accept a no-op only when independent review explicitly confirms no change is needed."""
    if not isinstance(review, dict):
        return False
    blockers = review.get("blockers")
    return bool(
        review.get("passed") is True
        and review.get("no_change_needed") is True
        and blockers == []
    )
