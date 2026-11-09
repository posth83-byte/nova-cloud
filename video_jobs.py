"""Small persistent job registry for long-running free video renders.

Job state is cached in memory for fast polling and mirrored to the existing
private Supabase Storage bucket as a tiny JSON object. No paid queue service is
required.
"""
import json
import os
import re
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

from video_storage import list_job_ids, open_stored_file, upload_file

_JOBS = {}


def save_job_status(job_id, status, *, result=None, error=None, request=None, worker_id=None):
    payload = {
        "job_id": job_id,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "result": result,
        "error": error,
        "request": request,
        "worker_id": worker_id,
    }
    _JOBS[job_id] = payload
    saved = False
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as stream:
            json.dump(payload, stream, ensure_ascii=False, separators=(",", ":"))
            temporary_path = Path(stream.name)
        try:
            saved = upload_file(job_id, temporary_path, "status.json", "application/json")
        finally:
            temporary_path.unlink(missing_ok=True)
    except Exception:
        saved = False
    payload["status_storage_status"] = "persistent" if saved else "memory_only"
    _JOBS[job_id] = payload
    return payload


def _expire_stale_job(payload):
    if payload.get("status") not in {"queued", "dispatched", "running"}:
        return payload
    try:
        updated = datetime.fromisoformat(payload.get("updated_at", ""))
    except (TypeError, ValueError):
        updated = datetime.min.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) - updated.astimezone(timezone.utc) > timedelta(minutes=15):
        return save_job_status(
            payload["job_id"], "failed",
            error="Videoprocessen avbröts troligen när Render startade om eller jobbet fastnade. Starta ett nytt videoförsök.",
            request=payload.get("request"),
        )
    return payload


def get_job_status(job_id):
    cached = _JOBS.get(job_id)
    if cached is not None:
        return _expire_stale_job(cached)
    remote = open_stored_file(job_id, "status.json")
    if remote is None:
        return None
    try:
        with remote:
            raw = remote.read(1_000_000)
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict) or payload.get("job_id") != job_id:
            return None
        payload["status_storage_status"] = "persistent"
        payload = _expire_stale_job(payload)
        _JOBS[job_id] = payload
        return payload
    except Exception:
        return None



def dispatch_github_video_job(job_id):
    """Dispatch rendering to a standard GitHub-hosted runner, not the tiny web instance."""
    token = (os.getenv("GITHUB_TOKEN") or "").strip()
    repository = (os.getenv("GITHUB_REPOSITORY") or "posth83-byte/nova-cloud").strip()
    if not token:
        raise RuntimeError("GITHUB_TOKEN saknas; kan inte starta den externa videorenderaren.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise RuntimeError("GITHUB_REPOSITORY har ett ogiltigt format.")
    url = f"https://api.github.com/repos/{repository}/dispatches"
    body = json.dumps({
        "event_type": "nova_video_render",
        "client_payload": {"job_id": job_id},
    }).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "Content-Type": "application/json",
            "User-Agent": "NOVA-Cloud-Video-Worker",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status != 204:
                raise RuntimeError(f"GitHub repository_dispatch returned HTTP {response.status}.")
    except urllib.error.HTTPError as error:
        detail = error.read(1200).decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub kunde inte starta videorenderaren (HTTP {error.code}): {detail}") from error
    return True


def recover_pending_jobs():
    """Find jobs saved before a Render restart but not yet claimed by a GitHub runner."""
    recovered = []
    for job_id in list_job_ids():
        payload = get_job_status(job_id)
        if not isinstance(payload, dict):
            continue
        status = payload.get("status")
        # A GitHub worker marks its claim with worker_id. It continues independently
        # of Render restarts, so never dispatch that active job a second time.
        if status not in {"queued", "dispatched", "running"} or payload.get("worker_id"):
            continue
        request = payload.get("request")
        if not isinstance(request, dict):
            continue
        required = {"topic", "mode", "video_type", "aspect", "duration_mode"}
        if not required.issubset(request):
            continue
        save_job_status(job_id, "queued", request=request)
        recovered.append({"job_id": job_id, **request})
    return recovered
