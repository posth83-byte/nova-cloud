"""Tests for the free persistent background-job status registry."""
import io
import json
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import video_jobs


def main():
    video_jobs._JOBS.clear()
    with patch.object(video_jobs, "upload_file", return_value=True) as upload:
        queued = video_jobs.save_job_status(
            "abc123abc123", "queued", request={"topic": "test"}
        )
        assert queued["status"] == "queued"
        assert queued["status_storage_status"] == "persistent"
        upload.assert_called_once()
        assert video_jobs.get_job_status("abc123abc123")["request"]["topic"] == "test"

    video_jobs._JOBS.clear()
    remote_payload = {
        "job_id": "abc123abc123",
        "status": "completed",
        "updated_at": "2026-11-09T12:00:00+00:00",
        "result": {"video_url": "/video.mp4"},
    }
    with patch.object(
        video_jobs, "open_stored_file",
        return_value=io.BytesIO(json.dumps(remote_payload).encode("utf-8"))
    ):
        recovered = video_jobs.get_job_status("abc123abc123")
    assert recovered and recovered["status"] == "completed"
    assert recovered["status_storage_status"] == "persistent"
    assert recovered["result"]["video_url"] == "/video.mp4"

    video_jobs._JOBS.clear()
    with patch.object(video_jobs, "upload_file", return_value=False):
        memory = video_jobs.save_job_status("def456def456", "queued")
    assert memory["status_storage_status"] == "memory_only"
    assert video_jobs.get_job_status("missing12345") is None
    print("PASS queued job state, private JSON persistence, remote recovery and memory-only fallback.")


if __name__ == "__main__":
    main()
