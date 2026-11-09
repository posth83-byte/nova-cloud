"""Free trend discovery and original short-video generation for JARVIS Video Team.

Trend discovery uses Google's public Trends RSS feed (Sweden). Original videos
are assembled locally with Pillow + FFmpeg and the already-installed Edge TTS
library; no paid video-generation API is called.
"""
import asyncio
import html
import re
import shutil
import subprocess
import uuid
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote_plus

import edge_tts
import imageio_ffmpeg
from fastapi import APIRouter, Form, HTTPException
from fastapi.responses import FileResponse
from PIL import Image, ImageDraw, ImageFont

router = APIRouter()
OUTPUT_DIR = Path("/tmp/nova_team_created")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
VOICE = "sv-SE-MattiasNeural"
W, H = 720, 1280
MAX_PROMPT = 220


def _ffmpeg(args, timeout=600):
    result = subprocess.run(
        [imageio_ffmpeg.get_ffmpeg_exe(), "-y", *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=timeout
    )
    if result.returncode:
        raise RuntimeError((result.stderr or "FFmpeg misslyckades.")[-1600:])


def _font(size, bold=False):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _wrap(draw, text, font, max_width):
    words = str(text).split()
    lines, current = [], ""
    for word in words:
        trial = (current + " " + word).strip()
        if current and draw.textbbox((0, 0), trial, font=font)[2] > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines


def _make_card(path, kicker, headline, line, index):
    image = Image.new("RGB", (W, H), (5, 11, 22))
    pixels = image.load()
    # Subtle vertical blue/orange gradient, generated locally.
    for y in range(H):
        t = y / H
        c = (int(7 + 18*t), int(18 + 8*t), int(36 + 5*t))
        for x in range(W):
            glow = max(0, 1 - (((x-W*0.5)/(W*.75))**2 + ((y-H*.35)/(H*.55))**2))
            pixels[x, y] = (min(255, c[0] + int(22*glow)), min(255, c[1] + int(35*glow)), min(255, c[2] + int(42*glow)))
    draw = ImageDraw.Draw(image)
    draw.ellipse((75, 150, 645, 720), outline=(255, 137, 67), width=3)
    draw.ellipse((115, 190, 605, 680), outline=(65, 183, 235), width=2)
    draw.rounded_rectangle((46, 55, 674, 125), radius=24, fill=(18, 38, 58), outline=(255, 145, 76), width=2)
    draw.text((W//2, 90), kicker.upper(), font=_font(25, True), fill=(255, 190, 132), anchor="mm")
    headline_font = _font(58 if index == 0 else 52, True)
    lines = _wrap(draw, headline, headline_font, 590)
    y = 400 - (len(lines) * 72)//2
    for item in lines[:5]:
        draw.text((W//2, y), item, font=headline_font, fill=(245, 250, 255), anchor="mm", stroke_width=1, stroke_fill=(7, 18, 32))
        y += 76
    line_font = _font(32, False)
    y2 = 850
    for item in _wrap(draw, line, line_font, 580)[:4]:
        draw.text((W//2, y2), item, font=line_font, fill=(177, 216, 239), anchor="mm")
        y2 += 46
    draw.text((W//2, 1175), "JARVIS VIDEO TEAM  •  ORIGINAL", font=_font(19, True), fill=(255, 156, 91), anchor="mm")
    image.save(path, quality=92)


def _build_script(topic):
    topic = re.sub(r"\s+", " ", (topic or "").strip())[:MAX_PROMPT].strip(" .!?")
    if not topic:
        topic = "vardagslivet"
    # Short, self-contained Swedish comedy structure with an original punchline.
    return [
        ("VÄNTA LITE…", f"Alla pratar om {topic}.", "Jag tänkte också haka på. Det gick… sådär."),
        ("PLANEN", "Jag hade en genialisk plan.", f"Den byggde på att {topic} skulle vara enkelt."),
        ("VERKLIGHETEN", "Tre sekunder senare:", "Självförtroendet var kvar. Kompetensen hade gått hem."),
        ("SLUTKLÄMMEN", "Så dagens lärdom?", "Om det verkar enkelt på internet – filma inte när du försöker."),
    ]


@router.get("/api/video/team/ideas")
def discover_video_ideas():
    """Fetch a small set of current Sweden trend topics from the public Trends RSS."""
    url = "https://trends.google.com/trending/rss?geo=SE"
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 NOVA-Cloud"})
    ideas = []
    source_error = None
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            payload = response.read(1_500_000)
        root = ET.fromstring(payload)
        for item in root.findall(".//item")[:12]:
            title = (item.findtext("title") or "").strip()
            if not title:
                continue
            traffic = (item.findtext("{https://trends.google.com/trending/rss}approx_traffic") or "").strip()
            link = (item.findtext("link") or "").strip()
            ideas.append({
                "title": title[:180],
                "traffic": traffic,
                "source": "Google Trends Sverige",
                "source_url": link or "https://trends.google.com/trending?geo=SE",
                "angle": "Gör en egen vardagshumorversion – inte en kopia av klippet eller innehållet."
            })
    except Exception as error:
        source_error = str(error)[:240]
    return {
        "status": "ok" if ideas else "unavailable",
        "source": "Google Trends Sverige",
        "ideas": ideas,
        "creative_center_url": "https://ads.tiktok.com/business/creativecenter/inspiration/popular/trends/pc/sv",
        "note": "Trenderna är sökintresse, inte verifierade TikTok-visningar. TikToks Creative Center kan öppnas separat.",
        "error": source_error
    }


@router.post("/api/video/team/create")
async def create_original_video(
    topic: str = Form(""),
    mode: str = Form("original"),
):
    topic = (topic or "").strip()
    if len(topic) > MAX_PROMPT:
        raise HTTPException(400, f"Ämnet får vara högst {MAX_PROMPT} tecken.")
    if mode not in {"original", "trend"}:
        raise HTTPException(400, "Ogiltigt videoläge.")
    if not topic:
        topic = "när man försöker vara produktiv"
    job_id = uuid.uuid4().hex[:12]
    job_dir = OUTPUT_DIR / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    try:
        beats = _build_script(topic)
        narration = " ".join(f"{heading}. {line} {punch}" for heading, line, punch in beats)
        narration_path = job_dir / "voice.mp3"
        await edge_tts.Communicate(narration, VOICE).save(str(narration_path))
        cards, clips = [], []
        for i, (heading, line, punch) in enumerate(beats):
            card = job_dir / f"scene_{i:02}.jpg"
            _make_card(card, heading, line, punch, i)
            cards.append(card)
        # Match scene lengths to the spoken beats, keeping a brisk short-form rhythm.
        durations = [6.2, 6.2, 6.2, 6.2]
        for i, (card, seconds) in enumerate(zip(cards, durations)):
            clip = job_dir / f"clip_{i:02}.mp4"
            frames = int(seconds * 25)
            _ffmpeg([
                "-loop", "1", "-i", str(card),
                "-vf", f"scale={W}:{H},zoompan=z='min(zoom+0.0007,1.045)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps=25,setsar=1",
                "-frames:v", str(frames), "-an", "-c:v", "libx264", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p", str(clip)
            ], timeout=180)
            clips.append(clip)
        concat = job_dir / "clips.txt"
        concat.write_text("".join(f"file '{clip.as_posix()}'\n" for clip in clips), encoding="utf-8")
        silent = job_dir / "silent.mp4"
        _ffmpeg(["-f", "concat", "-safe", "0", "-i", str(concat), "-c", "copy", str(silent)], timeout=180)
        output = job_dir / "jarvis_original.mp4"
        # Quiet, synthesized original music tones under Swedish narration.
        _ffmpeg([
            "-i", str(silent), "-i", str(narration_path),
            "-f", "lavfi", "-i", "sine=frequency=392:sample_rate=44100:duration=28",
            "-filter_complex", "[1:a]volume=1.0[voice];[2:a]volume=0.045[music];[voice][music]amix=inputs=2:duration=longest:dropout_transition=2[a]",
            "-map", "0:v:0", "-map", "[a]", "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-shortest", "-movflags", "+faststart", str(output)
        ], timeout=240)
        if not output.is_file() or output.stat().st_size < 10000:
            raise RuntimeError("MP4-filen saknas eller är ofullständig.")
        return {
            "status": "completed",
            "job_id": job_id,
            "mode": mode,
            "topic": topic,
            "script": [{"heading": h, "line": line, "punchline": punch} for h, line, punch in beats],
            "format": "9:16",
            "resolution": "720x1280",
            "voice": VOICE,
            "video_url": f"/api/video/team/created/{job_id}",
            "message": "En originalvideo med svensk berättarröst, animerade textscener och egen ljudmatta har skapats."
        }
    except HTTPException:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise
    except Exception as error:
        shutil.rmtree(job_dir, ignore_errors=True)
        raise HTTPException(502, f"Kunde inte skapa originalvideon: {str(error)[:700]}")


@router.get("/api/video/team/created/{job_id}")
def download_original_video(job_id: str):
    if not re.fullmatch(r"[a-f0-9]{12}", job_id):
        raise HTTPException(400, "Ogiltigt jobb-ID.")
    path = OUTPUT_DIR / job_id / "jarvis_original.mp4"
    if not path.is_file():
        raise HTTPException(404, "Originalvideon finns inte längre i Render-lagringen.")
    return FileResponse(path, media_type="video/mp4", filename="jarvis-original-tiktok.mp4")
