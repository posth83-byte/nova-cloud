"""Tests for private Supabase Storage uploads and streaming lookup."""
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import video_storage


class FakeResponse:
    status = 200
    def __init__(self, body=b""):
        self.body = body
    def read(self, size=-1):
        return self.body if size < 0 else self.body[:size]
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


def main():
    assert video_storage.MAX_UPLOAD_BYTES == 50 * 1024 * 1024
    with patch.dict(os.environ, {}, clear=True):
        assert not video_storage.is_configured()
        assert not video_storage.upload_file("abc123abc123", "/missing", "video.mp4", "video/mp4")
        assert video_storage.open_stored_file("abc123abc123", "video.mp4") is None

    env = {"SUPABASE_URL": "https://example.supabase.co", "SUPABASE_SECRET_KEY": "test-secret"}
    with tempfile.TemporaryDirectory() as folder, patch.dict(os.environ, env, clear=True):
        path = Path(folder) / "video.mp4"
        path.write_bytes(b"test-video")
        oversized = Path(folder) / "oversized.mp4"
        with oversized.open("wb") as stream:
            stream.truncate(video_storage.MAX_UPLOAD_BYTES + 1)
        with patch.object(video_storage, "_request") as blocked_request:
            assert not video_storage.upload_file("abc123abc123", oversized, "too-large.mp4", "video/mp4")
            blocked_request.assert_not_called()
        with patch.object(video_storage, "_request", return_value=FakeResponse()) as request:
            assert video_storage.upload_file("abc123abc123", path, "jarvis_original.mp4", "video/mp4")
            args, kwargs = request.call_args
            assert "/storage/v1/object/nova-videos/abc123abc123/jarvis_original.mp4" in args[0]
            assert kwargs["method"] == "POST"
            assert kwargs["content_type"] == "video/mp4"
        with patch.object(video_storage, "_request", return_value=FakeResponse()) as request:
            assert video_storage.open_stored_file("abc123abc123", "jarvis_original.mp4") is not None
            assert "/storage/v1/object/nova-videos/abc123abc123/jarvis_original.mp4" in request.call_args.args[0]

        with patch.object(video_storage, "_request", side_effect=[
            FakeResponse(), FakeResponse(b"NOVA private storage self-test"), FakeResponse()
        ]) as request:
            ok, message = video_storage.storage_self_test()
            assert ok, message
            assert [call.kwargs.get("method", "GET") for call in request.call_args_list] == ["POST", "GET", "DELETE"]
    print("PASS private storage configuration, upload/download/delete self-test and durable object lookup.")


if __name__ == "__main__":
    main()
