"""Live production smoke test for the free JARVIS video engine.

Runs only from GitHub Actions after a main-branch deployment. It creates one
small original video, verifies its MP4 audio/video streams, then downloads the
MP4 and subtitles directly from private Supabase Storage rather than local disk.
"""
import os
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urljoin

import imageio_ffmpeg
import requests

BASE_URL = os.getenv("JARVIS_BASE_URL", "https://nova-cloud-c4t9.onrender.com").rstrip("/")
TIMEOUT = (20, 600)


def wait_until_live():
    deadline = time.time() + 600
    last_error = "No response"
    while time.time() < deadline:
        try:
            response = requests.get(urljoin(BASE_URL + "/", "health"), timeout=20)
            if response.status_code == 200:
                print("PASS Render health endpoint is live.")
                return
            last_error = f"HTTP {response.status_code}"
        except requests.RequestException as error:
            last_error = str(error)
        time.sleep(10)
    raise RuntimeError(f"Render did not become healthy within 10 minutes: {last_error}")


def main():
    wait_until_live()
    response = requests.post(
        urljoin(BASE_URL + "/", "api/video/team/create"),
        data={
            "topic": "en rolig vardagsscen med kaffe",
            "mode": "original",
            "video_type": "humor",
            "aspect": "9:16",
            "duration_mode": "short",
        },
        timeout=TIMEOUT,
    )
    response.raise_for_status()
    queued = response.json()
    if queued.get("status") not in {"queued", "running", "completed"}:
        raise RuntimeError(f"Video engine did not queue a job: {queued}")
    if queued.get("status_storage_status") != "persistent":
        raise RuntimeError(
            "Video job state was not saved in private Supabase Storage. "
            f"Reported status_storage_status={queued.get('status_storage_status')!r}"
        )
    result = queued
    if queued.get("status") != "completed":
        status_url = urljoin(BASE_URL + "/", queued.get("status_url", f"/api/video/team/jobs/{queued.get('job_id', '')}").lstrip("/"))
        deadline = time.time() + 600
        while time.time() < deadline:
            time.sleep(4)
            status_response = requests.get(status_url, timeout=30)
            status_response.raise_for_status()
            job = status_response.json()
            if job.get("status") == "failed":
                raise RuntimeError(f"Background video job failed: {job.get('error')}")
            if job.get("status") == "completed":
                result = job.get("result") or {}
                break
        if result.get("status") != "completed":
            raise RuntimeError(f"Background video job did not finish within 10 minutes: {queued.get('job_id')}")
    if result.get("storage_status") != "persistent":
        raise RuntimeError(
            "MP4 was not saved in private Supabase Storage. "
            f"Reported storage_status={result.get('storage_status')!r}"
        )
    if result.get("subtitles_storage_status") != "persistent":
        raise RuntimeError(
            "SRT subtitles were not saved in private Supabase Storage. "
            f"Reported subtitles_storage_status={result.get('subtitles_storage_status')!r}"
        )

    job_id = result.get("job_id")
    if not job_id or len(job_id) != 12:
        raise RuntimeError("Video engine returned an invalid job ID.")

    video_url = urljoin(BASE_URL + "/", result["video_url"].lstrip("/"))
    subtitles_url = urljoin(BASE_URL + "/", result["subtitles_url"].lstrip("/"))
    with tempfile.TemporaryDirectory(prefix="jarvis-live-smoke-") as folder:
        video_path = Path(folder) / "production-smoke.mp4"
        # force_remote bypasses the Render local file and reads the private bucket.
        with requests.get(video_url, params={"force_remote": "true"}, stream=True, timeout=240) as download:
            download.raise_for_status()
            with video_path.open("wb") as output:
                for chunk in download.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        output.write(chunk)
        if video_path.stat().st_size < 10_000:
            raise RuntimeError(f"Remote MP4 download is unexpectedly small: {video_path.stat().st_size} bytes")

        decoded = subprocess.run(
            [
                imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(video_path),
                "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"
            ],
            capture_output=True, text=True, timeout=180,
        )
        if decoded.returncode:
            raise RuntimeError(f"Downloaded production MP4 did not decode: {decoded.stderr[-1500:]}")

        subtitles = requests.get(
            subtitles_url, params={"force_remote": "true"}, timeout=120
        )
        subtitles.raise_for_status()
        subtitle_text = subtitles.content.decode("utf-8-sig")
        if "-->" not in subtitle_text or len(subtitle_text.strip()) < 30:
            raise RuntimeError("Remote SRT download is missing valid timed subtitle cues.")

        print(
            "PASS live video generation; PASS private Supabase MP4 upload and remote retrieval; "
            f"PASS MP4 audio/video decode ({video_path.stat().st_size} bytes); "
            f"PASS private SRT upload and retrieval; job={job_id}; "
            f"format={result.get('format')}; resolution={result.get('resolution')}."
        )


if __name__ == "__main__":
    main()
