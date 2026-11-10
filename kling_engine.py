"""Secure server-side integration with the official Kling AI video API."""
import hmac
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
import uuid

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field
from video_cost_guard import paid_video_engines_enabled

router = APIRouter()

KLING_API_KEY = os.getenv("KLING_API_KEY", "").strip()
JARVIS_KLING_ACCESS_TOKEN = os.getenv("JARVIS_KLING_ACCESS_TOKEN", "").strip()
KLING_API_BASE = "https://api-singapore.klingai.com"


class KlingVideoRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=2500)
    aspect_ratio: str = Field(default="9:16")
    duration: int = Field(default=15, ge=3, le=15)
    resolution: str = Field(default="720p")
    audio: str = Field(default="off")
    multi_shot: bool = Field(default=False)


def require_kling_access(x_jarvis_access_token: str = Header(default="")):
    """Fail closed: never expose a paid generation endpoint without a server-side access token."""
    if not JARVIS_KLING_ACCESS_TOKEN:
        raise HTTPException(
            503,
            "Kling-integrationen är inte aktiverad: JARVIS_KLING_ACCESS_TOKEN saknas i Render."
        )
    if not x_jarvis_access_token or not hmac.compare_digest(
        x_jarvis_access_token, JARVIS_KLING_ACCESS_TOKEN
    ):
        raise HTTPException(401, "Ogiltig JARVIS-åtkomsttoken.")


def kling_request(path: str, method: str = "GET", payload=None):
    if not paid_video_engines_enabled():
        raise HTTPException(503, "Kling är avstängt för att skydda gratisläget. Den lokala procedurmotorn är standard.")
    if not KLING_API_KEY:
        raise HTTPException(
            503,
            "Kling är inte konfigurerat: KLING_API_KEY saknas i Render Environment."
        )
    headers = {
        "Authorization": "Bearer " + KLING_API_KEY,
        "Accept": "application/json"
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        KLING_API_BASE + path, data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
            result = json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise HTTPException(502, "Kling avvisade API-nyckeln eller dess behörighet.")
        if error.code == 402:
            raise HTTPException(402, "Kling-kontot saknar tillgängliga resurser/krediter.")
        if error.code == 429:
            raise HTTPException(429, "Kling begränsar just nu antalet API-anrop. Försök senare.")
        raise HTTPException(502, f"Kling API svarade med HTTP {error.code}.")
    except (urllib.error.URLError, TimeoutError):
        raise HTTPException(502, "JARVIS kunde inte nå Kling API just nu.")
    if not isinstance(result, dict) or result.get("code", 0) not in (0, "0", None):
        raise HTTPException(502, "Kling kunde inte behandla videouppdraget.")
    return result


@router.post("/api/kling/video")
def create_kling_video(
    request: KlingVideoRequest,
    x_jarvis_access_token: str = Header(default="")
):
    """Submit one explicitly requested Kling 3.0 video generation task."""
    require_kling_access(x_jarvis_access_token)
    if request.aspect_ratio not in ("9:16", "16:9", "1:1"):
        raise HTTPException(400, "Format måste vara 9:16, 16:9 eller 1:1.")
    if request.resolution not in ("720p", "1080p", "4k"):
        raise HTTPException(400, "Upplösningen måste vara 720p, 1080p eller 4k.")
    if request.audio not in ("off", "native"):
        raise HTTPException(400, "Ljud måste vara off eller native.")

    payload = {
        "prompt": request.prompt.strip(),
        "settings": {
            "resolution": request.resolution,
            "aspect_ratio": request.aspect_ratio,
            "duration": request.duration,
            "audio": request.audio,
            "multi_shot": request.multi_shot
        },
        "options": {
            "external_task_id": "jarvis-" + uuid.uuid4().hex,
            "watermark_info": {"enabled": False}
        }
    }
    result = kling_request("/text-to-video/kling-3.0", "POST", payload)
    data = result.get("data") or {}
    task_id = str(data.get("id") or "")
    if not task_id or not re.fullmatch(r"[A-Za-z0-9_-]{5,100}", task_id):
        raise HTTPException(502, "Kling tog inte emot uppdraget på ett igenkännbart sätt.")
    return {
        "provider": "Kling AI",
        "model": "kling-3.0",
        "status": data.get("status", "submitted"),
        "task_id": task_id,
        "aspect_ratio": request.aspect_ratio,
        "duration_seconds": request.duration,
        "resolution": request.resolution,
        "message": "Kling har tagit emot uppdraget. Hämta status via /api/kling/task/{task_id}."
    }


@router.get("/api/kling/task/{task_id}")
def get_kling_task(
    task_id: str,
    x_jarvis_access_token: str = Header(default="")
):
    """Read the status and result for a task created through this JARVIS service."""
    require_kling_access(x_jarvis_access_token)
    if not re.fullmatch(r"[A-Za-z0-9_-]{5,100}", task_id):
        raise HTTPException(400, "Ogiltigt Kling-jobb-ID.")
    result = kling_request(
        "/tasks?task_ids=" + urllib.parse.quote(task_id, safe=""),
        "GET"
    )
    rows = result.get("data") or []
    if isinstance(rows, dict):
        rows = rows.get("data") or rows.get("result") or []
    if not isinstance(rows, list) or not rows:
        raise HTTPException(404, "Kling-jobbet hittades inte.")
    task = next((item for item in rows if str(item.get("id")) == task_id), rows[0])
    outputs = task.get("outputs") or []
    videos = [
        {
            "url": item.get("url"),
            "watermark_url": item.get("watermark_url"),
            "duration": item.get("duration")
        }
        for item in outputs
        if isinstance(item, dict) and item.get("type") == "video"
    ]
    return {
        "provider": "Kling AI",
        "task_id": task_id,
        "status": task.get("status", "unknown"),
        "message": task.get("message"),
        "videos": videos,
        "billing": task.get("billing") or []
    }
