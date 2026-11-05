import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import urlparse

import edge_tts
import imageio_ffmpeg
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

router = APIRouter()
RUNWAY_API_KEY = os.getenv("RUNWAYML_API_SECRET", "").strip()
RUNWAY_BASE_URL = "https://api.dev.runwayml.com/v1"
RUNWAY_VERSION = "2024-11-06"
RUNWAY_VIDEO_DIR = Path(os.getenv("NOVA_RUNWAY_VIDEO_DIR", "/tmp/nova_runway_videos"))
RUNWAY_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
VOICE = os.getenv("NOVA_TTS_VOICE", "sv-SE-MattiasNeural")


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


class RunwayFinalizeRequest(BaseModel):
    task_ids: list[str] = Field(min_length=1, max_length=12)
    narration: str = Field(min_length=20, max_length=12000)


def runway_ffmpeg(args):
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    result = subprocess.run(
        [ffmpeg, "-y", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=900
    )
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "FFmpeg-fel")[-1800:])


def srt_time(seconds):
    millis = int(max(0, float(seconds)) * 1000)
    hours, millis = divmod(millis, 3600000)
    minutes, millis = divmod(millis, 60000)
    secs, millis = divmod(millis, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def build_srt(text, duration):
    import re as _re
    sentences = [part.strip() for part in _re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]
    if not sentences:
        raise RuntimeError("Berättarmanuset saknar text.")
    total = sum(max(1, len(part)) for part in sentences)
    cursor = 0.0
    blocks = []
    for number, sentence in enumerate(sentences, 1):
        span = duration * max(1, len(sentence)) / total
        start = cursor
        end = min(duration, cursor + span)
        blocks.append(f"{number}\n{srt_time(start)} --> {srt_time(end)}\n{sentence}\n")
        cursor = end
    return "\n".join(blocks)


@router.post("/api/runway/finalize")
async def finalize_runway_video(request: RunwayFinalizeRequest):
    """Download successful Runway tasks and assemble them with Swedish narration."""
    job_id = uuid.uuid4().hex[:12]
    job_dir = RUNWAY_VIDEO_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    try:
        clip_paths = []
        seen = set()
        for index, task_id in enumerate(request.task_ids):
            if not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", task_id):
                raise HTTPException(400, "Ett Runway-jobb-ID har fel format.")
            if task_id in seen:
                continue
            seen.add(task_id)
            task = runway_request("/tasks/" + task_id)
            if str(task.get("status", "")).upper() != "SUCCEEDED":
                raise HTTPException(409, f"Runway-jobbet {task_id} är inte färdigt ännu.")
            outputs = task.get("output") or []
            if isinstance(outputs, str):
                outputs = [outputs]
            if not outputs:
                raise HTTPException(502, f"Runway-jobbet {task_id} saknar videofil.")
            output_url = outputs[0]
            parsed = urlparse(output_url)
            if parsed.scheme != "https" or not parsed.hostname:
                raise HTTPException(502, "Runway returnerade en ogiltig videolänk.")
            clip_path = job_dir / f"scene_{index:02}.mp4"
            download_request = urllib.request.Request(
                output_url,
                headers={"User-Agent": "NOVA-Cloud/3.0"}
            )
            total_bytes = 0
            try:
                with urllib.request.urlopen(download_request, timeout=120) as response:
                    with clip_path.open("wb") as output:
                        while True:
                            chunk = response.read(1024 * 1024)
                            if not chunk:
                                break
                            total_bytes += len(chunk)
                            if total_bytes > 150 * 1024 * 1024:
                                raise HTTPException(413, "Ett Runway-klipp överskrider gränsen på 150 MB.")
                            output.write(chunk)
            except urllib.error.URLError as error:
                raise HTTPException(502, f"Kunde inte hämta Runway-klippet: {str(error)[:400]}")
            if total_bytes < 10000:
                raise HTTPException(502, "Runway returnerade en tom eller ofullständig videofil.")
            clip_paths.append(clip_path)

        if not clip_paths:
            raise HTTPException(400, "Inga färdiga Runway-klipp valdes.")

        concat_file = job_dir / "clips.txt"
        concat_file.write_text(
            "".join(f"file '{path.as_posix()}'\n" for path in clip_paths),
            encoding="utf-8"
        )
        silent_video = job_dir / "scenes.mp4"
        runway_ffmpeg([
            "-f", "concat", "-safe", "0", "-i", str(concat_file),
            "-an", "-c:v", "libx264", "-preset", "veryfast",
            "-pix_fmt", "yuv420p", "-r", "25", "-movflags", "+faststart",
            str(silent_video)
        ])

        narration_path = job_dir / "narration.mp3"
        await edge_tts.Communicate(request.narration, VOICE).save(str(narration_path))

        final_video = job_dir / "nova_runway_video.mp4"
        runway_ffmpeg([
            "-i", str(silent_video), "-i", str(narration_path),
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", "-movflags", "+faststart", str(final_video)
        ])

        subtitles_path = job_dir / "undertexter.srt"
        # Approximate subtitle timing across the finished visual timeline.
        subtitle_duration = max(1, len(clip_paths) * 5)
        subtitles_path.write_text(
            build_srt(request.narration, subtitle_duration),
            encoding="utf-8"
        )

        if not final_video.exists() or final_video.stat().st_size < 10000:
            raise RuntimeError("Den färdiga MP4-filen skapades inte korrekt.")

        return {
            "status": "completed",
            "job_id": job_id,
            "clip_count": len(clip_paths),
            "voice": VOICE,
            "video_url": f"/api/runway/download/{job_id}",
            "subtitles_url": f"/api/runway/subtitles/{job_id}",
            "message": "Runway-klippen har satts ihop med svensk berättarröst."
        }
    except HTTPException:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise
    except Exception as error:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(500, f"Kunde inte sätta ihop Runway-videon: {str(error)[:900]}")


@router.get("/api/runway/download/{job_id}")
def download_runway_video(job_id: str):
    if not re.fullmatch(r"[a-f0-9]{12}", job_id):
        raise HTTPException(400, "Ogiltigt jobb-ID.")
    path = RUNWAY_VIDEO_DIR / job_id / "nova_runway_video.mp4"
    if not path.is_file():
        raise HTTPException(404, "Videon finns inte längre i Render-lagringen.")
    return FileResponse(path, media_type="video/mp4", filename="nova_runway_video.mp4")


@router.get("/api/runway/subtitles/{job_id}")
def download_runway_subtitles(job_id: str):
    if not re.fullmatch(r"[a-f0-9]{12}", job_id):
        raise HTTPException(400, "Ogiltigt jobb-ID.")
    path = RUNWAY_VIDEO_DIR / job_id / "undertexter.srt"
    if not path.is_file():
        raise HTTPException(404, "Undertexterna finns inte längre i Render-lagringen.")
    return FileResponse(path, media_type="application/x-subrip", filename="nova-undertexter.srt")
