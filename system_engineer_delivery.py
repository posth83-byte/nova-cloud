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


def is_runtime_evidence_verified(
    evidence: dict,
    source_commit_sha: str,
    status_route_in_source: bool,
    required: bool = True,
) -> bool:
    """Fail closed unless machine-captured HTTP and source evidence match the locked commit."""
    if not required:
        return True
    if not isinstance(evidence, dict) or not status_route_in_source:
        return False
    try:
        http_status = int(evidence.get("http_status") or 0)
    except (TypeError, ValueError):
        return False
    expected_commit = str(source_commit_sha or "")[:12]
    actual_commit = str(evidence.get("deployment_commit") or "")
    return bool(
        evidence.get("status") == "verified"
        and http_status == 200
        and len(expected_commit) == 12
        and actual_commit == expected_commit
    )



def build_evidence_reconciliation(task: str, qa_evidence: dict, specialist_results=None) -> dict:
    """Reconcile machine-captured QA facts before an AI reviewer can approve a delivery."""
    task_text = str(task or "").casefold()
    runtime_required = (
        "/api/status" in task_text
        and any(term in task_text for term in ("driftsatt", "live", "runtime", "returnerar", "http"))
    )
    evidence = qa_evidence if isinstance(qa_evidence, dict) else {}
    source_commit = str(evidence.get("source_commit_sha") or "")
    source_files = evidence.get("source_files_fetched")
    source_verified = bool(
        evidence.get("source_snapshot_status") == "fetched"
        and len(source_commit) >= 12
        and isinstance(source_files, list)
        and "main.py" in source_files
        and evidence.get("status_route_in_qa_source") is True
    )
    captures = []
    for key in ("runtime_status_endpoint", "post_qa_status_endpoint"):
        capture = evidence.get(key)
        if isinstance(capture, dict) and capture:
            captures.append({"stage": key, "verified": is_runtime_evidence_verified(
                capture, source_commit, source_verified, required=True
            ), "http_status": capture.get("http_status"),
                "deployment_commit": str(capture.get("deployment_commit") or ""),
                "status": str(capture.get("status") or "")})
    if not runtime_required:
        runtime_verified = None
        status = "not_required"
    else:
        runtime_verified = bool(
            source_verified
            and captures
            and all(item["verified"] for item in captures)
        )
        status = "verified" if runtime_verified else "blocked"
    return {
        "runtime_required": runtime_required,
        "runtime_status": status,
        "runtime_verified": runtime_verified,
        "source_snapshot_verified": source_verified,
        "source_commit_sha": source_commit or None,
        "runtime_captures": captures,
        "specialist_reports_are_not_runtime_evidence": True,
        "interpretation": (
            "Specialisterna saknar direkt nätverksverktyg i sina textanalyser. "
            "Deras beskrivning av egen verktygsåtkomst motsäger inte ett separat "
            "maskininsamlat QA-resultat. Endast QA-underlagets verifierade HTTP- och "
            "källkodsbevis avgör runtime-status."
        )
    }


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
