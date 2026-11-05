import json
import os
import re
import urllib.error
import urllib.request

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()
RUNWAY_API_KEY = os.getenv("RUNWAYML_API_SECRET", "").strip()
RUNWAY_BASE_URL = "https://api.dev.runwayml.com/v1"
RUNWAY_VERSION = "2024-11-06"


class RunwaySceneRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=5000)
    image_data: str = Field(default="", max_length=6_800_000)
    aspect: str = Field(default="16:9")
    duration: int = Field(default=5, ge=5, le=10)


def runway_request(path: str, method: str = "GET", payload=None):
    if not RUNWAY_API_KEY:
        raise HTTPException(503, "Runway är inte konfigurerat i Render.")

    headers = {
        "Authorization": f"Bearer {RUNWAY_API_KEY}",
        "X-Runway-Version": RUNWAY_VERSION,
        "Accept": "application/json"
    }
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        RUNWAY_BASE_URL + path, data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        if error.code in (401, 403):
            raise HTTPException(502, "Runway avvisade anslutningen. Kontrollera API-nyckelns behörighet.")
        if error.code == 402:
            raise HTTPException(402, "Runway-kontot saknar krediter för videogenerering.")
        if error.code == 429:
            raise HTTPException(429, "Runway har tillfälligt begränsat antalet förfrågningar. Försök senare.")
        raise HTTPException(502, f"Runway API-fel ({error.code}): {details[:900]}")
    except (urllib.error.URLError, TimeoutError) as error:
        raise HTTPException(502, f"Kunde inte nå Runway: {str(error)[:500]}")


def get_credit_balance():
    account = runway_request("/organization")
    balance = account.get("creditBalance")
    if balance is None:
        raise HTTPException(503, "Runway svarade men kreditbalansen kunde inte läsas. Ingen generering startades.")
    try:
        return int(balance)
    except (TypeError, ValueError):
        raise HTTPException(503, "Runway returnerade en okänd kreditbalans. Ingen generering startades.")


@router.post("/api/runway/scene")
def create_runway_scene(request: RunwaySceneRequest):
    """Start one explicitly requested paid Runway video task."""
    if request.aspect not in ("16:9", "9:16"):
        raise HTTPException(400, "Videoformat måste vara 16:9 eller 9:16.")

    image_data = request.image_data.strip()
    if image_data:
        if not image_data.startswith((
            "data:image/jpeg;base64,", "data:image/png;base64,", "data:image/webp;base64,"
        )):
            raise HTTPException(400, "Referensbilden måste vara JPG, PNG eller WebP.")
        if len(image_data) > 5_000_000:
            raise HTTPException(413, "Runways referensbild får vara högst 5 MB.")

    # Stop before creating a task when there are no credits.
    balance = get_credit_balance()
    if balance <= 0:
        raise HTTPException(
            402,
            "Runway-kontot har 0 krediter. Ingen videogenerering har startats och inget har debiterats."
        )

    payload = {
        "model": "gen4.5",
        "promptText": request.prompt.strip(),
        "ratio": "1280:720" if request.aspect == "16:9" else "720:1280",
        "duration": request.duration
    }
    if image_data:
        payload["promptImage"] = image_data
        endpoint = "/image_to_video"
    else:
        endpoint = "/text_to_video"

    task = runway_request(endpoint, method="POST", payload=payload)
    task_id = task.get("id")
    if not task_id:
        raise HTTPException(502, "Runway startade inget igenkännbart videjobb. Kontrollera kontot innan du försöker igen.")

    return {
        "status": "submitted",
        "task_id": task_id,
        "model": "gen4.5",
        "estimated_cost": task.get("estimatedCost"),
        "credit_balance_before": balance,
        "message": "Runway har tagit emot scenen. Kontrollera jobbstatus för att följa genereringen."
    }


@router.get("/api/runway/task/{task_id}")
def get_runway_task(task_id: str):
    if not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", task_id):
        raise HTTPException(400, "Ogiltigt Runway-jobb-ID.")
    task = runway_request("/tasks/" + task_id)
    output = task.get("output") or []
    if isinstance(output, str):
        output = [output]
    return {
        "task_id": task_id,
        "status": task.get("status", "UNKNOWN"),
        "output": output,
        "failure": task.get("failure"),
        "failure_code": task.get("failureCode"),
        "progress": task.get("progress")
    }
