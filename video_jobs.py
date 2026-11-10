"""Small persistent job registry for long-running free video renders.

Job state is cached in memory for fast polling and mirrored to the existing
private Supabase Storage bucket as a tiny JSON object. No paid queue service is
required.
"""
import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

from video_storage import list_job_ids, open_stored_file, upload_file

_JOBS = {}


def save_job_status(job_id, status, *, result=None, error=None, request=None):
    payload = {
        "job_id": job_id,
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "result": result,
        "error": error,
        "request": request,
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
    if payload.get("status") not in {"queued", "running"}:
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



def recover_pending_jobs():
    """Resume queued jobs and safely stop jobs interrupted by a process restart."""
    recovered = []
    required = {"topic", "mode", "video_type", "aspect", "duration_mode"}
    for job_id in list_job_ids():
        payload = get_job_status(job_id)
        if not isinstance(payload, dict):
            continue
        status = payload.get("status")
        request = payload.get("request")
        if status == "running":
            # A running FFmpeg process belonged to the previous server process.
            # Replaying it after an OOM/restart can create an endless crash loop.
            save_job_status(
                job_id, "failed",
                error="Render avbröts medan videon renderades. Jobbet startas inte om automatiskt för att undvika en ny minneskrasch. Skapa ett nytt försök.",
                request=request if isinstance(request, dict) else None,
            )
            continue
        if status != "queued":
            continue
        if not isinstance(request, dict) or not required.issubset(request):
            save_job_status(
                job_id, "failed",
                error="Videokön innehöll ett ofullständigt jobb som inte kunde återupptas.",
                request=request if isinstance(request, dict) else None,
            )
            continue
        # Queued work has not started rendering and is safe to resume.
        save_job_status(job_id, "queued", request=request)
        recovered.append({"job_id": job_id, **request})
    return recovered
