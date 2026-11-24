"""Guarded exact-text patch helpers for SYSTEM_ENGINEER's GitHub delivery path."""

from __future__ import annotations

import re
from typing import Iterable


def select_independent_review_provider(generation_engine: str, gemini_available: bool, openrouter_available: bool):
    """Choose a different provider for code review; never silently self-review."""
    engine = str(generation_engine or "").strip().lower()
    if engine.startswith("gemini"):
        return "OpenRouter" if openrouter_available else None
    if engine.startswith("openrouter"):
        return "Gemini" if gemini_available else None
    return None



def has_route_decorator(source: str, path: str) -> bool:
    """Match a real top-level FastAPI GET decorator, not a string/comment mention."""
    route_path = str(path or "").strip()
    if not route_path.startswith("/") or '"' in route_path:
        return False
    pattern = r'(?m)^@app\.get\("' + re.escape(route_path) + r'"\)\s*
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



def task_requires_live_runtime_evidence(task: str) -> bool:
    """Detect explicit live/runtime verification intent, including Swedish drift terminology."""
    task_text = str(task or "").casefold()
    return bool(
        "/api/status" in task_text
        and any(term in task_text for term in (
            "drift", "live", "runtime", "http", "endpoint", "verifier",
            "kontroll", "check", "health", "test"
        ))
    )


def build_evidence_reconciliation(task: str, qa_evidence: dict, specialist_results=None) -> dict:
    """Reconcile every explicitly requested endpoint against source and two runtime captures."""
    task_text = str(task or "").casefold()
    runtime_required = task_requires_live_runtime_evidence(task_text)
    known_endpoints = (
        "/api/status",
        "/api/jarvis/intelligence",
        "/api/worker/status",
        "/api/memory/status",
        "/api/team/status",
    )
    requested_endpoints = [path for path in known_endpoints if path in task_text]
    evidence = qa_evidence if isinstance(qa_evidence, dict) else {}
    source_commit = str(evidence.get("source_commit_sha") or "")
    source_files = evidence.get("source_files_fetched")
    source_routes = evidence.get("runtime_routes_in_qa_source")
    source_verified = bool(
        evidence.get("source_snapshot_status") == "fetched"
        and len(source_commit) >= 12
        and isinstance(source_files, list)
        and "main.py" in source_files
        and evidence.get("status_route_in_qa_source") is True
    )
    if source_verified:
        for path in requested_endpoints:
            if path != "/api/status" and (
                not isinstance(source_routes, list) or path not in source_routes
            ):
                source_verified = False
                break

    captures = []
    for key in ("runtime_status_endpoint", "post_qa_status_endpoint"):
        capture = evidence.get(key)
        captures.append({
            "stage": key,
            "verified": is_runtime_evidence_verified(
                capture, source_commit, source_verified, required=True
            ),
            "http_status": capture.get("http_status") if isinstance(capture, dict) else None,
            "deployment_commit": str(capture.get("deployment_commit") or "") if isinstance(capture, dict) else "",
            "status": str(capture.get("status") or "") if isinstance(capture, dict) else "",
        })

    endpoint_checks = []
    for stage_key in ("runtime_endpoints", "post_qa_runtime_endpoints"):
        stage = evidence.get(stage_key)
        for path in requested_endpoints:
            if path == "/api/status":
                continue
            capture = stage.get(path) if isinstance(stage, dict) else None
            valid = bool(
                isinstance(capture, dict)
                and capture.get("status") == "verified"
                and str(capture.get("http_status") or "") == "200"
            )
            endpoint_checks.append({
                "stage": stage_key,
                "endpoint": path,
                "verified": valid,
                "http_status": capture.get("http_status") if isinstance(capture, dict) else None,
                "status": str(capture.get("status") or "") if isinstance(capture, dict) else "missing",
            })

    if not runtime_required:
        runtime_verified = None
        status = "not_required"
    else:
        runtime_verified = bool(
            source_verified
            and all(item["verified"] for item in captures)
            and all(item["verified"] for item in endpoint_checks)
        )
        status = "verified" if runtime_verified else "blocked"
    return {
        "runtime_required": runtime_required,
        "runtime_status": status,
        "runtime_verified": runtime_verified,
        "requested_endpoints": requested_endpoints,
        "source_snapshot_verified": source_verified,
        "source_commit_sha": source_commit or None,
        "runtime_captures": captures,
        "endpoint_captures": endpoint_checks,
        "specialist_reports_are_not_runtime_evidence": True,
        "interpretation": (
            "Endast maskininsamlad HTTP- och källkodsevidens räknas. Varje uttryckligen "
            "begärd endpoint måste vara verifierad i både första och andra runtime-avläsningen. "
            "Specialisternas egna verktygsbegränsningar ersätter inte eller motsäger dessa bevis."
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

    return bool(re.search(pattern, str(source or "")))

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



def task_requires_live_runtime_evidence(task: str) -> bool:
    """Detect explicit live/runtime verification intent, including Swedish drift terminology."""
    task_text = str(task or "").casefold()
    return bool(
        "/api/status" in task_text
        and any(term in task_text for term in (
            "drift", "live", "runtime", "http", "endpoint", "verifier",
            "kontroll", "check", "health", "test"
        ))
    )


def build_evidence_reconciliation(task: str, qa_evidence: dict, specialist_results=None) -> dict:
    """Reconcile every explicitly requested endpoint against source and two runtime captures."""
    task_text = str(task or "").casefold()
    runtime_required = task_requires_live_runtime_evidence(task_text)
    known_endpoints = (
        "/api/status",
        "/api/jarvis/intelligence",
        "/api/worker/status",
        "/api/memory/status",
        "/api/team/status",
    )
    requested_endpoints = [path for path in known_endpoints if path in task_text]
    evidence = qa_evidence if isinstance(qa_evidence, dict) else {}
    source_commit = str(evidence.get("source_commit_sha") or "")
    source_files = evidence.get("source_files_fetched")
    source_routes = evidence.get("runtime_routes_in_qa_source")
    source_verified = bool(
        evidence.get("source_snapshot_status") == "fetched"
        and len(source_commit) >= 12
        and isinstance(source_files, list)
        and "main.py" in source_files
        and evidence.get("status_route_in_qa_source") is True
    )
    if source_verified:
        for path in requested_endpoints:
            if path != "/api/status" and (
                not isinstance(source_routes, list) or path not in source_routes
            ):
                source_verified = False
                break

    captures = []
    for key in ("runtime_status_endpoint", "post_qa_status_endpoint"):
        capture = evidence.get(key)
        captures.append({
            "stage": key,
            "verified": is_runtime_evidence_verified(
                capture, source_commit, source_verified, required=True
            ),
            "http_status": capture.get("http_status") if isinstance(capture, dict) else None,
            "deployment_commit": str(capture.get("deployment_commit") or "") if isinstance(capture, dict) else "",
            "status": str(capture.get("status") or "") if isinstance(capture, dict) else "",
        })

    endpoint_checks = []
    for stage_key in ("runtime_endpoints", "post_qa_runtime_endpoints"):
        stage = evidence.get(stage_key)
        for path in requested_endpoints:
            if path == "/api/status":
                continue
            capture = stage.get(path) if isinstance(stage, dict) else None
            valid = bool(
                isinstance(capture, dict)
                and capture.get("status") == "verified"
                and str(capture.get("http_status") or "") == "200"
            )
            endpoint_checks.append({
                "stage": stage_key,
                "endpoint": path,
                "verified": valid,
                "http_status": capture.get("http_status") if isinstance(capture, dict) else None,
                "status": str(capture.get("status") or "") if isinstance(capture, dict) else "missing",
            })

    if not runtime_required:
        runtime_verified = None
        status = "not_required"
    else:
        runtime_verified = bool(
            source_verified
            and all(item["verified"] for item in captures)
            and all(item["verified"] for item in endpoint_checks)
        )
        status = "verified" if runtime_verified else "blocked"
    return {
        "runtime_required": runtime_required,
        "runtime_status": status,
        "runtime_verified": runtime_verified,
        "requested_endpoints": requested_endpoints,
        "source_snapshot_verified": source_verified,
        "source_commit_sha": source_commit or None,
        "runtime_captures": captures,
        "endpoint_captures": endpoint_checks,
        "specialist_reports_are_not_runtime_evidence": True,
        "interpretation": (
            "Endast maskininsamlad HTTP- och källkodsevidens räknas. Varje uttryckligen "
            "begärd endpoint måste vara verifierad i både första och andra runtime-avläsningen. "
            "Specialisternas egna verktygsbegränsningar ersätter inte eller motsäger dessa bevis."
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
