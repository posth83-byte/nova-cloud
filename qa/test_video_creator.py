"""Integration checks for the procedural short-video renderer."""
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

    assert len(engine._build_script("kaffet tar slut")) == 5
    assert len(engine._build_script("sova")) == 5
    assert len(engine._build_script("vardagslivet")) == 5
    for kind in ("explainer", "tutorial", "promo", "inspiration", "story"):
        assert len(engine._build_script("solenergi", kind)) == 5, kind
        assert "solenergi" in " ".join(beat[1] for beat in engine._build_script("solenergi", kind)).casefold()
    assert "PANG!" not in engine._motion_filter("generic", 1, "tutorial")
    for topic, expected in (("träning på gymmet", "gym"), ("lön och budget", "money"),
                            ("första dejten", "love"), ("laga middag", "food")):
        beats = engine._build_script(topic)
        assert len(beats) == 5, (topic, beats)
        assert expected in {beat[3] for beat in beats}, (topic, beats)
    assert len({beat[3] for beat in engine._build_script("lön och budget")}) >= 4
    assert len({beat[3] for beat in engine._build_script("första dejten")}) >= 3
    animated_filter = engine._motion_filter("coffee", 2, "humor")
    assert "zoompan=" in animated_filter and "drawtext=" in animated_filter
    assert "sin(t*" in animated_filter and "fade=t=in" in animated_filter
    assert "SLURP!" in animated_filter and "between(t," in animated_filter
    assert "ZZZ!" in engine._motion_filter("sleep", 0)
    assert "PANG!" in engine._motion_filter("generic", 1)

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
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100:duration=28",
                    "-c:a", "libmp3lame", "-b:a", "64k", str(path)
                ]
                completed = subprocess.run(command, capture_output=True, text=True, timeout=60)
                if completed.returncode:
                    raise RuntimeError(completed.stderr[-1200:])

        with patch.object(engine, "search_commons_images", return_value=[]), patch.object(engine.edge_tts, "Communicate", LocalSpeechFixture):
            result = asyncio.run(engine.create_original_video(
                topic="när kaffet tar slut precis när jobbet börjar", mode="original", video_type="humor"))

        assert result["status"] == "completed", result
        assert result["format"] == "9:16"
        assert result["video_type"] == "humor"
        assert result["resolution"] == "720x1280"
        assert len(result["script"]) == 5
        job_dir = Path(temporary) / result["job_id"]
        output = job_dir / "jarvis_original.mp4"
        assert output.is_file() and output.stat().st_size > 10000
        assert len(list(job_dir.glob("scene_*.jpg"))) == 5
        decode = subprocess.run(
            [engine.imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(output), "-f", "null", "-"],
            capture_output=True, text=True, timeout=120)
        assert decode.returncode == 0, decode.stderr
        response = engine.download_original_video(result["job_id"])
        assert Path(response.path) == output
        try:
            engine.download_original_video("../invalid")
        except Exception as error:
            assert getattr(error, "status_code", None) == 400
        else:
            raise AssertionError("Invalid job IDs must be rejected.")
        print(f"PASS trend parsing; PASS five-scene procedural render; PASS MP4 decode ({output.stat().st_size} bytes); PASS download route.")
        engine.OUTPUT_DIR = original_output


if __name__ == "__main__":
    main()
