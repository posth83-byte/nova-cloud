"""Integration checks for the free original short-video renderer.

Uses a locally synthesized speech fixture so CI does not depend on an external
TTS provider. The real Render path still uses Edge TTS.
"""
import asyncio
import io
import subprocess
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import video_creator_engine as engine


def main():
    rss = b"""<?xml version='1.0' encoding='UTF-8'?>
    <rss xmlns:ht='https://trends.google.com/trending/rss'><channel>
      <item><title>Exempeltrend Sverige</title><ht:approx_traffic>20K+</ht:approx_traffic>
      <link>https://trends.google.com/trending?geo=SE</link></item>
    </channel></rss>"""
    with patch.object(engine.urllib.request, "urlopen", return_value=io.BytesIO(rss)):
        trends = engine.discover_video_ideas()
    assert trends["status"] == "ok", trends
    assert trends["ideas"][0]["title"] == "Exempeltrend Sverige"
    assert trends["ideas"][0]["traffic"] == "20K+"

    original_output = engine.OUTPUT_DIR
    with tempfile.TemporaryDirectory(prefix="jarvis-video-test-") as temporary:
        engine.OUTPUT_DIR = Path(temporary)

        class LocalSpeechFixture:
            def __init__(self, text, voice):
                assert voice == engine.VOICE
                assert text

            async def save(self, path):
                command = [
                    engine.imageio_ffmpeg.get_ffmpeg_exe(), "-y",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=22",
                    "-c:a", "libmp3lame", "-b:a", "64k", str(path)
                ]
                completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
                if completed.returncode:
                    raise RuntimeError(completed.stderr[-1200:])

        with patch.object(engine.edge_tts, "Communicate", LocalSpeechFixture):
            result = asyncio.run(engine.create_original_video(
                topic="när kaffet tar slut precis när jobbet börjar",
                mode="original"
            ))

        assert result["status"] == "completed", result
        assert result["format"] == "9:16"
        assert result["resolution"] == "720x1280"
        assert len(result["script"]) == 4
        job_dir = Path(temporary) / result["job_id"]
        output = job_dir / "jarvis_original.mp4"
        assert output.is_file() and output.stat().st_size > 10000
        assert len(list(job_dir.glob("scene_*.jpg"))) == 4

        # Decode the complete exported MP4 to catch corrupt or truncated output.
        decode = subprocess.run(
            [engine.imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(output), "-f", "null", "-"],
            capture_output=True, text=True, timeout=90
        )
        assert decode.returncode == 0, decode.stderr

        response = engine.download_original_video(result["job_id"])
        assert Path(response.path) == output
        try:
            engine.download_original_video("../invalid")
        except Exception as error:
            assert getattr(error, "status_code", None) == 400
        else:
            raise AssertionError("Invalid job IDs must be rejected.")

        print(
            "PASS trend RSS parsing; PASS four-scene Swedish short-video render; "
            f"PASS MP4 decode ({output.stat().st_size} bytes); PASS download route."
        )
        engine.OUTPUT_DIR = original_output


if __name__ == "__main__":
    main()
