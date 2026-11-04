
import os
import re
import shutil
import subprocess
import uuid
from pathlib import Path
from typing import List, Optional

import edge_tts
import imageio_ffmpeg
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image

router = APIRouter()

VIDEO_DIR = Path(os.getenv("NOVA_VIDEO_DIR", "/tmp/nova_videos"))
VIDEO_DIR.mkdir(parents=True, exist_ok=True)

FPS = 25
VOICE = os.getenv("NOVA_TTS_VOICE", "sv-SE-MattiasNeural")
MAX_IMAGES = 12
MAX_IMAGE_BYTES = 12 * 1024 * 1024


def run_ffmpeg(args: list[str]) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    result = subprocess.run(
        [ffmpeg, "-y", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=900
    )

    if result.returncode != 0:
        raise RuntimeError(
            (result.stderr or "Okänt FFmpeg-fel")[-2500:]
        )


def get_duration(path: Path) -> float:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    result = subprocess.run(
        [ffmpeg, "-i", str(path), "-f", "null", "-"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=60
    )

    match = re.search(
        r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)",
        result.stderr or ""
    )

    if not match:
        raise RuntimeError("Kunde inte läsa ljudfilens längd.")

    hours, minutes, seconds = match.groups()

    return (
        int(hours) * 3600
        + int(minutes) * 60
        + float(seconds)
    )


def make_srt_time(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))

    hours, milliseconds = divmod(milliseconds, 3600000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    secs, milliseconds = divmod(milliseconds, 1000)

    return (
        f"{hours:02}:"
        f"{minutes:02}:"
        f"{secs:02},"
        f"{milliseconds:03}"
    )


def create_subtitles(text: str, duration: float, path: Path):
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        raise RuntimeError("Manuset saknar text.")

    total_weight = sum(max(1, len(s)) for s in sentences)
    current_time = 0.0
    blocks = []

    for index, sentence in enumerate(sentences, 1):
        weight = max(1, len(sentence))
        sentence_duration = duration * weight / total_weight

        start = current_time
        end = min(duration, current_time + sentence_duration)

        blocks.append(
            f"{index}\n"
            f"{make_srt_time(start)} --> "
            f"{make_srt_time(end)}\n"
            f"{sentence}\n"
        )

        current_time = end

    path.write_text("\n".join(blocks), encoding="utf-8")


async def save_image(upload: UploadFile, destination: Path):
    size = 0

    with destination.open("wb") as output:
        while True:
            chunk = await upload.read(1024 * 1024)

            if not chunk:
                break

            size += len(chunk)

            if size > MAX_IMAGE_BYTES:
                raise HTTPException(
                    413,
                    "En bild får vara högst 12 MB."
                )

            output.write(chunk)

    try:
        with Image.open(destination) as image:
            image.verify()
    except Exception:
        destination.unlink(missing_ok=True)

        raise HTTPException(
            415,
            "En uppladdad fil är inte en giltig bild."
        )


def create_scene(
    image_path: Path,
    output_path: Path,
    seconds: float,
    width: int,
    height: int
):
    frames = max(25, int(seconds * FPS))

    video_filter = (
        f"scale={width}:{height}:"
        "force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        "zoompan="
        "z='min(zoom+0.0005,1.08)':"
        "x='iw/2-(iw/zoom/2)':"
        "y='ih/2-(ih/zoom/2)':"
        f"d={frames}:"
        f"s={width}x{height}:"
        f"fps={FPS},"
        "setsar=1"
    )

    run_ffmpeg([
        "-loop", "1",
        "-i", str(image_path),
        "-vf", video_filter,
        "-frames:v", str(frames),
        "-r", str(FPS),
        "-an",
        "-c:v", "libx264",
        "-preset", "ultrafast",
        "-pix_fmt", "yuv420p",
        str(output_path)
    ])


@router.post("/api/video/render")
async def render_video(
    narration: str = Form(...),
    aspect: str = Form("16:9"),
    images: List[UploadFile] = File(...),
    music: Optional[UploadFile] = File(None)
):
    narration = narration.strip()

    if len(narration) < 20:
        raise HTTPException(
            400,
            "Manuset behöver innehålla minst 20 tecken."
        )

    if len(narration) > 6000:
        raise HTTPException(
            400,
            "Manuset får vara högst 6000 tecken."
        )

    if not images or len(images) > MAX_IMAGES:
        raise HTTPException(
            400,
            f"Ladda upp mellan 1 och {MAX_IMAGES} bilder."
        )

    if aspect not in ("16:9", "9:16"):
        raise HTTPException(
            400,
            "Format måste vara 16:9 eller 9:16."
        )

    job_id = uuid.uuid4().hex[:12]
    job_dir = VIDEO_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)

    width, height = (
        (1280, 720)
        if aspect == "16:9"
        else (720, 1280)
    )

    try:
        image_paths = []

        for index, upload in enumerate(images):
            suffix = Path(upload.filename or "").suffix.lower()

            if suffix not in (".jpg", ".jpeg", ".png", ".webp"):
                suffix = ".jpg"

            image_path = job_dir / f"scene_{index:02}{suffix}"

            await save_image(upload, image_path)
            image_paths.append(image_path)

        narration_path = job_dir / "narration.mp3"

        speech = edge_tts.Communicate(
            narration,
            VOICE
        )

        await speech.save(str(narration_path))

        duration = get_duration(narration_path)

        if duration <= 0:
            raise RuntimeError("Berättarrösten saknar giltig längd.")

        scene_duration = duration / len(image_paths)
        clips = []

        for index, image_path in enumerate(image_paths):
            clip_path = job_dir / f"clip_{index:02}.mp4"

            create_scene(
                image_path,
                clip_path,
                scene_duration,
                width,
                height
            )

            clips.append(clip_path)

        concat_file = job_dir / "clips.txt"

        concat_file.write_text(
            "".join(
                f"file '{clip.as_posix()}'\n"
                for clip in clips
            ),
            encoding="utf-8"
        )

        silent_video = job_dir / "silent.mp4"

        run_ffmpeg([
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-r", str(FPS),
            str(silent_video)
        ])

        video_path = job_dir / "nova_video.mp4"

        if music is not None:
            music_path = job_dir / "music_upload"

            with music_path.open("wb") as output:
                while True:
                    chunk = await music.read(1024 * 1024)

                    if not chunk:
                        break

                    output.write(chunk)

            run_ffmpeg([
                "-i", str(silent_video),
                "-i", str(narration_path),
                "-stream_loop", "-1",
                "-i", str(music_path),
                "-filter_complex",
                "[1:a]volume=1.0[voice];"
                "[2:a]volume=0.16[music];"
                "[voice][music]amix=inputs=2:"
                "duration=first:dropout_transition=2[a]",
                "-map", "0:v",
                "-map", "[a]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-movflags", "+faststart",
                str(video_path)
            ])

        else:
            run_ffmpeg([
                "-i", str(silent_video),
                "-i", str(narration_path),
                "-map", "0:v",
                "-map", "1:a",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-shortest",
                "-movflags", "+faststart",
                str(video_path)
            ])

        subtitle_path = job_dir / "undertexter.srt"

        create_subtitles(
            narration,
            duration,
            subtitle_path
        )

        if not video_path.exists() or video_path.stat().st_size < 10000:
            raise RuntimeError("MP4-filen skapades inte korrekt.")

        return {
            "status": "completed",
            "job_id": job_id,
            "production_status": "video_ready",
            "render_status": "completed",
            "format": aspect,
            "duration_seconds": round(duration, 1),
            "voice": VOICE,
            "video_url": f"/api/video/download/{job_id}",
            "subtitles_url": f"/api/video/subtitles/{job_id}",
            "message": "Videon har renderats."
        }

    except HTTPException:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise

    except Exception as exc:
        shutil.rmtree(job_dir, ignore_errors=True)

        raise HTTPException(
            500,
            f"Videorenderingen misslyckades: {str(exc)[:1200]}"
        )


@router.get("/api/video/download/{job_id}")
def download_video(job_id: str):
    if not re.fullmatch(r"[a-f0-9]{12}", job_id):
        raise HTTPException(400, "Ogiltigt jobb-ID.")

    path = VIDEO_DIR / job_id / "nova_video.mp4"

    if not path.is_file():
        raise HTTPException(
            404,
            "Videon finns inte kvar i Render-lagringen."
        )

    return FileResponse(
        path,
        media_type="video/mp4",
        filename="nova_video.mp4"
    )


@router.get("/api/video/subtitles/{job_id}")
def download_subtitles(job_id: str):
    if not re.fullmatch(r"[a-f0-9]{12}", job_id):
        raise HTTPException(400, "Ogiltigt jobb-ID.")

    path = VIDEO_DIR / job_id / "undertexter.srt"

    if not path.is_file():
        raise HTTPException(
            404,
            "Undertextfilen finns inte kvar i Render-lagringen."
        )

    return FileResponse(
        path,
        media_type="application/x-subrip",
        filename="undertexter.srt"
    )
