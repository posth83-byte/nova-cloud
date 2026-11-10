"""Integration checks for the procedural short-video renderer."""
import asyncio
import io
import subprocess
import tempfile
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

from PIL import Image

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
    assert "zoompan=" in animated_filter and "drawtext=" not in animated_filter
    assert "sin(on/" in animated_filter and "fade=t=in" in animated_filter
    assert engine.CHARACTER_REACTIONS["coffee"] == "VA?!"
    assert engine._character_punchline_start(5.2) == 4.32
    assert engine._character_punchline_start(2.0) == 1.12
    assert (engine.W, engine.H, engine.FPS) == (540, 960, 20)
    assert engine.CHARACTER_FPS == 10
    for aspect in ("9:16", "16:9", "1:1"):
        assert 0 <= engine._character_overlay_x(aspect) <= engine.W - 184
    start_pose = engine._draw_character_frame("coffee", 0, 0.2, 5.2)
    moving_pose = engine._draw_character_frame("coffee", 0, 1.4, 5.2)
    punchline_pose = engine._draw_character_frame("coffee", 0, 4.7, 5.2)
    assert start_pose.mode == "RGBA" and start_pose.size == (184, 250)
    assert start_pose.getbbox(), "The procedural character frame must not be empty."
    assert start_pose.tobytes() != moving_pose.tobytes(), "The character must move between frames."
    assert moving_pose.tobytes() != punchline_pose.tobytes(), "The punchline must change the character pose."

    original_output = engine.OUTPUT_DIR
    with tempfile.TemporaryDirectory(prefix="jarvis-video-test-") as temporary:
        engine.OUTPUT_DIR = Path(temporary)
        preview = Path(temporary) / "scene-layout.jpg"
        engine._make_scene(preview, "TEST", "Rubrik i bild", "Punchline i bild", "coffee", 0)
        with Image.open(preview) as scene_preview:
            assert scene_preview.size == (engine.W, engine.H)
            assert (
                scene_preview.getpixel((270, 750)) != scene_preview.getpixel((270, 660))
            ), "The scaled subtitle panel must remain visible inside the frame."
            assert (
                scene_preview.getpixel((480, 750)) != scene_preview.getpixel((480, 660))
            ), "The subtitle panel must span the full design width."
        character_pattern = engine._write_character_frames(Path(temporary), "coffee", 0, 2.0)
        character_frames = sorted(character_pattern.parent.glob("frame_*.png"))
        assert len(character_frames) == 20
        assert len({frame.read_bytes() for frame in character_frames}) > 1

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
            result = asyncio.run(engine._render_original_video(
                "när kaffet tar slut precis när jobbet börjar", "original", "humor",
                "9:16", "standard", uuid.uuid4().hex[:12]))

        assert result["status"] == "completed", result
        assert result["format"] == "9:16"
        assert result["video_type"] == "humor"
        assert result["resolution"] == "540x960"
        assert len(result["script"]) == 5
        job_dir = Path(temporary) / result["job_id"]
        output = job_dir / "jarvis_original.mp4"
        assert output.is_file() and output.stat().st_size > 10000
        assert len(list(job_dir.glob("scene_*.jpg"))) == 5
        rendered_character_frames = sorted((job_dir / "character_00").glob("frame_*.png"))
        assert len(rendered_character_frames) >= 45, "Comedy scenes must include the animated character sequence."
        decode = subprocess.run(
            [engine.imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(output), "-f", "null", "-"],
            capture_output=True, text=True, timeout=120)
        assert decode.returncode == 0, decode.stderr
        response = engine.download_original_video(result["job_id"])
        assert Path(response.path) == output
        subtitles = job_dir / "undertexter.srt"
        assert subtitles.is_file()
        subtitle_text = subtitles.read_text(encoding="utf-8")
        assert " --> " in subtitle_text and "kaffemaskinen" in subtitle_text
        assert len([line for line in subtitle_text.splitlines() if line.isdigit()]) > 5
        subtitle_response = engine.download_video_subtitles(result["job_id"])
        assert Path(subtitle_response.path) == subtitles

        wide = asyncio.run(engine._render_original_video(
            "när kaffet tar slut precis när jobbet börjar",
            "original", "humor", "16:9", "standard", uuid.uuid4().hex[:12]))
        assert wide["status"] == "completed", wide
        assert wide["format"] == "16:9" and wide["resolution"] == "960x540"
        wide_path = Path(temporary) / wide["job_id"] / "jarvis_original.mp4"
        assert wide_path.is_file() and wide_path.stat().st_size > 10000
        wide_decode = subprocess.run(
            [engine.imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(wide_path), "-f", "null", "-"],
            capture_output=True, text=True, timeout=120)
        assert wide_decode.returncode == 0, wide_decode.stderr

        square = asyncio.run(engine._render_original_video(
            "när kaffet tar slut precis när jobbet börjar",
            "original", "humor", "1:1", "standard", uuid.uuid4().hex[:12]))
        assert square["status"] == "completed", square
        assert square["format"] == "1:1" and square["resolution"] == "720x720"
        square_path = Path(temporary) / square["job_id"] / "jarvis_original.mp4"
        assert square_path.is_file() and square_path.stat().st_size > 10000
        square_decode = subprocess.run(
            [engine.imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-i", str(square_path), "-f", "null", "-"],
            capture_output=True, text=True, timeout=120)
        assert square_decode.returncode == 0, square_decode.stderr
        try:
            engine.download_original_video("../invalid")
        except Exception as error:
            assert getattr(error, "status_code", None) == 400
        else:
            raise AssertionError("Invalid job IDs must be rejected.")
        print(f"PASS trend parsing; PASS vertical, landscape and square MP4 renders; PASS SRT subtitles; PASS MP4 decode ({output.stat().st_size} bytes).")
        engine.OUTPUT_DIR = original_output


if __name__ == "__main__":
    main()
