"""Small persistent job registry for long-running free video renders.

Job state is cached in memory for fast polling and mirrored to the existing
private Supabase Storage bucket as a tiny JSON object. No paid queue service is
required.
"""
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from video_storage import open_stored_file, upload_file

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


def get_job_status(job_id):
    cached = _JOBS.get(job_id)
    if cached is not None:
        return cached
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
        _JOBS[job_id] = payload
        return payload
    except Exception:
        return None
