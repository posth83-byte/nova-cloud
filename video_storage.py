"""Private Supabase Storage for durable NOVA video outputs.

The service-role/secret key is read only from server environment variables and
is never returned to the browser. If storage is not configured, callers retain
the existing local temporary-file behavior.
"""
import os
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BUCKET = "nova-videos"
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


def _credentials():
    base = os.getenv("SUPABASE_URL", "").strip().rstrip("/")
    key = (os.getenv("SUPABASE_SECRET_KEY", "").strip()
           or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip())
    if not base or not key:
        return None
    return base, key


def is_configured():
    return _credentials() is not None


def _request(path, key, method="GET", data=None, content_type=None):
    headers = {
        "apikey": key,
        "Authorization": "Bearer " + key,
    }
    if content_type:
        headers["Content-Type"] = content_type
    if method in ("POST", "PUT"):
        headers["x-upsert"] = "true"
    request = urllib.request.Request(path, data=data, headers=headers, method=method)
    return urllib.request.urlopen(request, timeout=90)


def upload_file(job_id, local_path, object_name, content_type):
    """Upload one generated artifact to the private bucket; return success."""
    credentials = _credentials()
    if not credentials:
        return False
    path = Path(local_path)
    if not path.is_file() or path.stat().st_size > MAX_UPLOAD_BYTES:
        return False
    base, key = credentials
    object_path = urllib.parse.quote(f"{job_id}/{object_name}", safe="/")
    url = f"{base}/storage/v1/object/{BUCKET}/{object_path}"
    try:
        with _request(url, key, method="POST", data=path.read_bytes(),
                      content_type=content_type) as response:
            return 200 <= response.status < 300
    except Exception:
        return False


def open_stored_file(job_id, object_name):
    """Open a private object for server-side streaming; caller closes response."""
    credentials = _credentials()
    if not credentials:
        return None
    base, key = credentials
    object_path = urllib.parse.quote(f"{job_id}/{object_name}", safe="/")
    url = f"{base}/storage/v1/object/{BUCKET}/{object_path}"
    try:
        return _request(url, key)
    except Exception:
        return None
