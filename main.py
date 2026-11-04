
import os
import json
import re
import uuid
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field
from video_engine import router as video_router


# ==========================================
# NOVA CLOUD – VERSION 2.2.0
# ==========================================

APP_VERSION = "2.9.0"

app = FastAPI(
    title="NOVA Cloud",
    description="JARVIS och NOVA – personlig AI-central",
    version=APP_VERSION
)

app.include_router(video_router)

# Temporary previews are cleared when the service restarts.
preview_pages = {}


# ==========================================
# INSTÄLLNINGAR
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv(
    "GEMINI_MODEL",
    "gemini-3.5-flash-lite"
)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv(
    "OPENROUTER_MODEL",
    "openai/gpt-4o-mini"
)

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_CHANNEL_HANDLE = os.getenv(
    "YOUTUBE_CHANNEL_HANDLE",
    "mikaelposth"
).strip().lstrip("@")

YOUTUBE_CHANNEL_IDS = [
    item.strip()
    for item in os.getenv(
        "YOUTUBE_CHANNEL_IDS", ""
    ).replace(";", ",").split(",")
    if item.strip()
]

MAX_RSS_CHANNELS = 15
MAX_RSS_VIDEOS = 60


def resolve_youtube_channel_ids():
    """Resolve the configured channel handle to a YouTube channel ID."""
    ids = [
        item for item in YOUTUBE_CHANNEL_IDS
        if item.startswith("UC") and len(item) == 24
    ]

    if not YOUTUBE_API_KEY or not YOUTUBE_CHANNEL_HANDLE:
        return ids

    url = (
        "https://www.googleapis.com/youtube/v3/channels"
        "?part=id"
        f"&forHandle={quote(YOUTUBE_CHANNEL_HANDLE)}"
        f"&key={quote(YOUTUBE_API_KEY)}"
    )
    req = urllib.request.Request(
        url,
        headers={"User-Agent": f"NOVA-Cloud/{APP_VERSION}"}
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
        for item in result.get("items", []):
            channel_id = item.get("id")
            if channel_id and channel_id not in ids:
                ids.append(channel_id)
    except Exception:
        # Keep manually configured IDs available if handle lookup fails.
        pass

    return ids[:MAX_RSS_CHANNELS]


# ==========================================
# MODELLER
# ==========================================

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)


class NovaChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    reference_url: str = Field(default="", max_length=2000)
    reference_image_data: str = Field(default="", max_length=5600000)


class WebPreviewRequest(BaseModel):
    html: str = Field(min_length=20, max_length=2000000)


class VideoPlanRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=5000)
    channel: str = "Mikael Posth"
    format: str = "long"
    duration_minutes: int = Field(default=5, ge=1, le=30)
    style: str = "Engagerande och professionell"
    audience: str = "Svensk YouTube-publik"
    reference_url: str = Field(default="", max_length=2000)
    reference_image_data: str = Field(default="", max_length=6000000)


# ==========================================
# AI-PERSONLIGHETER
# ==========================================

JARVIS_PROMPT = """
Du är JARVIS, en avancerad personlig AI-assistent.

Du kommunicerar på naturlig svenska.
Du är lugn, intelligent, professionell,
vänlig, analytisk och lösningsorienterad.

Du hjälper användaren med teknik, vardag,
planering, research och personliga projekt.

Du samarbetar med NOVA, som ansvarar för
kreativ produktion och YouTube-projekt.

Ge tydliga och praktiska svar.
Undvik onödigt långa förklaringar.
Ta ett steg i taget när det behövs.
"""

NOVA_PROMPT = """
Du är NOVA, en avancerad kreativ AI-producent.

Du utvecklar YouTube-kanalen:
- Mikael Posth

Du ansvarar för:
- Trendanalys och videoidéer
- Research och faktakontroll
- Professionella videomanus
- Scenindelning och bildprompter
- Berättarröster och undertexter
- Videoproduktion
- Titlar, thumbnails och SEO
- Analys av YouTube-innehåll
- Strategier för kanalutveckling.

Prioritera idéer som fångar tittaren snabbt,
skapar engagemang och kan produceras effektivt.

VIKTIGA REGLER:
- Hitta aldrig på statistik.
- Skilj fakta från bedömningar.
- Hitta aldrig på källor.
- Ange när data saknas.
- Påstå aldrig att du har producerat eller
  publicerat något som du inte faktiskt gjort.

Du kommunicerar på naturlig svenska.
"""

VIDEO_PRODUCER_PROMPT = """
Du är NOVA VIDEO PRODUCER, en professionell
AI-regissör, manusförfattare och videoproducent.

Ditt uppdrag är att skapa ett komplett
produktionsunderlag för en YouTube-video.

Du ska skapa:
1. En stark och engagerande idé.
2. En öppning som fångar tittaren direkt.
3. Ett komplett berättarmanus på svenska.
4. En tydlig scenindelning.
5. Bildprompter för varje scen.
6. Videoprompter för varje scen.
7. Kameravinklar och rörelseförslag.
8. Förslag på musik och ljudeffekter.
9. Undertexter med tidsangivelser.
10. YouTube-titel och beskrivning.
11. Thumbnail-idé och bildprompt.
12. Relevanta sökord och hashtags.

BERÄTTARSTIL:
Skriv naturlig, levande svenska.
Undvik robotliknande formuleringar.
Manuset ska vara lätt att läsa upp.
Variera tempo och meningslängd.
Skapa nyfikenhet och behåll tittarens intresse.

SCENER:
Varje scen ska ha:
- scene_number
- title
- start_seconds
- end_seconds
- narration
- visual_description
- image_prompt
- video_prompt
- camera
- sound_effects
- music

UNDERtexter:
Skapa undertexter som följer berättarrösten.
Använd start_seconds, end_seconds och text.

FORMAT:
Returnera ENDAST giltig JSON.
Ingen Markdown.
Inga kodstaket.
Inga kommentarer före eller efter JSON.

Använd exakt följande struktur:

{
  "title": "Videotitel",
  "concept": "Beskrivning av videon",
  "hook": "Öppning",
  "target_audience": "Målgrupp",
  "estimated_duration_seconds": 300,
  "narration_style": "Beskriv rösten",
  "full_narration": "Hela berättarmanuset",
  "scenes": [
    {
      "scene_number": 1,
      "title": "Scenens namn",
      "start_seconds": 0,
      "end_seconds": 30,
      "narration": "Berättarröst",
      "visual_description": "Vad tittaren ser",
      "image_prompt": "Detaljerad bildprompt",
      "video_prompt": "Detaljerad videoprompt",
      "camera": "Kamerarörelse",
      "sound_effects": "Ljudeffekter",
      "music": "Musikförslag"
    }
  ],
  "subtitles": [
    {
      "start_seconds": 0,
      "end_seconds": 5,
      "text": "Undertext"
    }
  ],
  "thumbnail": {
    "concept": "Thumbnail-idé",
    "image_prompt": "Bildprompt",
    "text": "Text på bilden"
  },
  "youtube": {
    "title": "YouTube-titel",
    "description": "Beskrivning",
    "tags": ["ord1", "ord2"],
    "hashtags": ["#exempel"]
  }
}

Skapa tillräckligt många scener för videons längd.
Håll tidsangivelserna sammanhängande.
Anpassa manusets längd till önskad speltid.
"""

TREND_PROMPT = NOVA_PROMPT


# ==========================================
# GEMINI MOTOR
# ==========================================

def ask_gemini(
    message,
    system_prompt,
    max_tokens=2048,
    json_mode=False,
    image_data=""
):

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{GEMINI_MODEL}:generateContent"
    )

    generation_config = {
        "temperature": 0.4 if json_mode else 0.7,
        "maxOutputTokens": max_tokens
    }

    if json_mode:
        generation_config["responseMimeType"] = "application/json"

    user_parts = [{"text": message}]
    if image_data:
        try:
            header, encoded_image = image_data.split(",", 1)
            mime_type = header.split(";", 1)[0].replace("data:", "")
            if mime_type not in ("image/jpeg", "image/png", "image/webp"):
                raise ValueError("Referensbilden måste vara JPG, PNG eller WebP.")
            user_parts.append({"inline_data": {"mime_type": mime_type, "data": encoded_image}})
        except ValueError:
            raise
        except Exception as error:
            raise ValueError(f"Kunde inte läsa referensbilden: {error}")

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": user_parts}],
        "generationConfig": generation_config
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise ValueError(
            f"Gemini API-fel {error.code}: {details[:1500]}"
        )

    candidates = result.get("candidates", [])

    if not candidates:
        raise ValueError("Gemini skickade inget svar.")

    candidate = candidates[0]

    finish_reason = candidate.get("finishReason", "")

    if finish_reason == "MAX_TOKENS":
        raise ValueError(
            "Gemini avbröt svaret eftersom token-gränsen nåddes."
        )

    parts = candidate.get("content", {}).get("parts", [])

    answer = " ".join(
        part.get("text", "")
        for part in parts
        if part.get("text")
    ).strip()

    if not answer:
        raise ValueError(
            f"Gemini skickade ett tomt svar. Orsak: {finish_reason}"
        )

    return answer


# ==========================================
# OPENROUTER RESERVMOTOR
# ==========================================

def ask_openrouter(
    message,
    system_prompt,
    max_tokens=2048,
    json_mode=False,
    image_data=""
):

    url = "https://openrouter.ai/api/v1/chat/completions"

    user_content = message
    if image_data:
        user_content = [
            {"type": "text", "text": message},
            {"type": "image_url", "image_url": {"url": image_data}}
        ]

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ],
        "temperature": 0.4 if json_mode else 0.7,
        "max_tokens": max_tokens
    }

    if json_mode:
        payload["response_format"] = {
            "type": "json_object"
        }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {OPENROUTER_API_KEY}"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        raise ValueError(
            f"OpenRouter API-fel {error.code}: {details[:1500]}"
        )

    choices = result.get("choices", [])

    if not choices:
        raise ValueError("OpenRouter skickade inget svar.")

    choice = choices[0]

    if choice.get("finish_reason") == "length":
        raise ValueError(
            "OpenRouter avbröt svaret på grund av token-gränsen."
        )

    answer = choice.get("message", {}).get("content", "")

    if isinstance(answer, list):
        answer = " ".join(
            item.get("text", "")
            for item in answer
            if isinstance(item, dict)
        )

    answer = str(answer).strip()

    if not answer:
        raise ValueError("OpenRouter skickade ett tomt svar.")

    return answer


# ==========================================
# GEMENSAM AI-FUNKTION
# ==========================================

def generate_reply(
    message,
    system_prompt,
    max_tokens=2048,
    json_mode=False,
    image_data=""
):

    gemini_error = None

    if GEMINI_API_KEY:
        try:
            try:
                answer = ask_gemini(
                    message,
                    system_prompt,
                    max_tokens,
                    json_mode,
                    image_data
                )
            except ValueError as error:
                # Retry once with a larger output budget when Gemini truncates.
                if "token-gränsen nåddes" not in str(error).lower() or max_tokens >= 16384:
                    raise
                retry_tokens = min(max_tokens * 2, 16384)
                answer = ask_gemini(
                    message,
                    system_prompt,
                    retry_tokens,
                    json_mode,
                    image_data
                )

            return {
                "reply": answer,
                "engine": "Gemini"
            }

        except Exception as error:
            gemini_error = str(error)

    else:
        gemini_error = "Gemini API-nyckel saknas."

    if OPENROUTER_API_KEY:
        try:
            return {
                "reply": ask_openrouter(
                    message,
                    system_prompt,
                    max_tokens,
                    json_mode,
                    image_data
                ),
                "engine": "OpenRouter"
            }

        except Exception as error:
            raise HTTPException(
                status_code=502,
                detail=(
                    "Både Gemini och OpenRouter misslyckades. "
                    f"Gemini: {gemini_error}. "
                    f"OpenRouter: {str(error)}"
                )
            )

    raise HTTPException(
        status_code=503,
        detail=(
            "Ingen AI-motor kunde svara. "
            f"Gemini: {gemini_error}. "
            "OpenRouter är inte konfigurerat."
        )
    )


# ==========================================
# VIDEO – JSON HANTERING
# ==========================================

def extract_json(text):

    cleaned = str(text).strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(
        r"\s*```$",
        "",
        cleaned
    )

    start = cleaned.find("{")

    if start == -1:
        raise ValueError(
            "AI-svaret innehöll ingen JSON."
        )

    decoder = json.JSONDecoder()

    try:
        result, _ = decoder.raw_decode(cleaned[start:])

        if not isinstance(result, dict):
            raise ValueError(
                "Videopaketet måste vara ett JSON-objekt."
            )

        return result

    except json.JSONDecodeError as error:

        position = start + error.pos

        snippet = cleaned[
            max(0, position - 100):
            min(len(cleaned), position + 100)
        ]

        raise ValueError(
            f"JSON-fel på rad {error.lineno}, "
            f"kolumn {error.colno}. "
            f"Text runt felet: {snippet}"
        )


def repair_video_json(broken_text):

    repair_prompt = """
Du är en JSON-reparatör.

Din uppgift är att reparera JSON-texten nedan.

REGLER:
- Returnera endast giltig JSON.
- Behåll allt innehåll som går att rädda.
- Hitta inte på nya fakta.
- Ta bort kommentarer och Markdown.
- Rätta felaktiga kommatecken och citationstecken.
- Säkerställ att alla strängar är korrekt avslutade.
- Säkerställ att alla objekt och listor stängs.
- Ändra inte JSON-strukturens fältnamn.

Returnera endast det kompletta JSON-objektet.
"""

    repair_message = (
        "Reparera följande JSON:\n\n"
        + str(broken_text)[:30000]
    )

    result = generate_reply(
        repair_message,
        repair_prompt,
        max_tokens=8192,
        json_mode=True
    )

    return extract_json(result["reply"])


# ==========================================
# VIDEO – VALIDERING
# ==========================================

def seconds_to_srt(seconds):

    milliseconds = int(float(seconds) * 1000)

    hours = milliseconds // 3600000
    milliseconds %= 3600000

    minutes = milliseconds // 60000
    milliseconds %= 60000

    secs = milliseconds // 1000
    millis = milliseconds % 1000

    return (
        f"{hours:02d}:{minutes:02d}:"
        f"{secs:02d},{millis:03d}"
    )


def create_srt(subtitles):

    lines = []

    for index, item in enumerate(subtitles, start=1):

        start = seconds_to_srt(item["start_seconds"])
        end = seconds_to_srt(item["end_seconds"])
        text = str(item.get("text", "")).strip()

        lines.extend([
            str(index),
            f"{start} --> {end}",
            text,
            ""
        ])

    return "\n".join(lines)


def validate_video_plan(plan):

    required = [
        "title",
        "concept",
        "full_narration",
        "scenes",
        "subtitles",
        "thumbnail",
        "youtube"
    ]

    if not isinstance(plan, dict):
        raise ValueError("Videoplanen har fel format.")

    for key in required:
        if key not in plan:
            raise ValueError(
                f"Videoplanen saknar fältet: {key}"
            )

    if not isinstance(plan["scenes"], list) or not plan["scenes"]:
        raise ValueError("Videoplanen saknar scener.")

    if not isinstance(plan["subtitles"], list):
        raise ValueError("Undertexterna har fel format.")

    if not isinstance(plan["thumbnail"], dict):
        raise ValueError("Thumbnail har fel format.")

    if not isinstance(plan["youtube"], dict):
        raise ValueError("YouTube-informationen har fel format.")

    for scene in plan["scenes"]:

        if not isinstance(scene, dict):
            raise ValueError("En scen har fel format.")

        for key in [
            "scene_number",
            "title",
            "start_seconds",
            "end_seconds",
            "narration",
            "visual_description",
            "image_prompt",
            "video_prompt"
        ]:
            if key not in scene:
                raise ValueError(
                    f"En scen saknar fältet: {key}"
                )

    for subtitle in plan["subtitles"]:

        if not isinstance(subtitle, dict):
            raise ValueError("En undertext har fel format.")

        for key in [
            "start_seconds",
            "end_seconds",
            "text"
        ]:
            if key not in subtitle:
                raise ValueError(
                    f"En undertext saknar fältet: {key}"
                )

    return plan


# ==========================================
# TRENDKÄLLA 1 – GOOGLE TRENDS
# ==========================================

def get_google_trends():

    url = "https://trends.google.com/trending/rss?geo=SE"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 NOVA-Cloud/2.3"
        }
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        xml_data = response.read()

    root = ET.fromstring(xml_data)

    results = []

    for item in root.findall(".//item")[:20]:

        title = item.findtext("title")
        link = item.findtext("link")
        pub_date = item.findtext("pubDate")

        if title:
            results.append({
                "title": title,
                "url": link,
                "published": pub_date,
                "source": "Google Trends Sverige"
            })

    return results


# ==========================================
# TRENDKÄLLA 2 – YOUTUBE RSS
# ==========================================

def get_youtube_rss():

    videos = []
    errors = []
    channels_checked = 0

    valid_ids = resolve_youtube_channel_ids()

    configured_valid_ids = [
        item for item in YOUTUBE_CHANNEL_IDS
        if item.startswith("UC") and len(item) == 24
    ]
    invalid_count = max(0, len(YOUTUBE_CHANNEL_IDS) - len(configured_valid_ids))

    if invalid_count:
        errors.append(
            f"{invalid_count} kanal-ID:n hade fel format."
        )

    for channel_id in valid_ids[:MAX_RSS_CHANNELS]:

        url = (
            "https://www.youtube.com/feeds/videos.xml"
            f"?channel_id={quote(channel_id)}"
        )

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Mozilla/5.0 NOVA-Cloud/2.2"
                }
            )

            with urllib.request.urlopen(req, timeout=20) as response:
                xml_data = response.read()

            root = ET.fromstring(xml_data)

            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "yt": "http://www.youtube.com/xml/schemas/2015"
            }

            feed_title = root.findtext(
                "atom:title",
                default="Okänd kanal",
                namespaces=ns
            )

            channels_checked += 1

            for entry in root.findall("atom:entry", ns):

                video_id = entry.findtext(
                    "yt:videoId",
                    namespaces=ns
                )

                title = entry.findtext(
                    "atom:title",
                    default="",
                    namespaces=ns
                )

                published = entry.findtext(
                    "atom:published",
                    default=None,
                    namespaces=ns
                )

                author = entry.find(
                    "atom:author/atom:name",
                    ns
                )

                channel_name = (
                    author.text if author is not None
                    else feed_title
                )

                if not video_id or not title:
                    continue

                videos.append({
                    "title": title,
                    "channel": channel_name,
                    "channel_id": channel_id,
                    "published": published,
                    "video_id": video_id,
                    "url": (
                        f"https://www.youtube.com/watch?v={video_id}"
                    ),
                    "source": "YouTube RSS",
                    "statistics_available": False
                })

        except Exception as error:
            errors.append(
                f"YouTube RSS ({channel_id}): {str(error)}"
            )

    unique_videos = []
    seen = set()

    for video in videos:

        video_id = video["video_id"]

        if video_id not in seen:
            seen.add(video_id)
            unique_videos.append(video)

    unique_videos.sort(
        key=lambda item: item.get("published") or "",
        reverse=True
    )

    return {
        "videos": unique_videos[:MAX_RSS_VIDEOS],
        "channels_checked": channels_checked,
        "errors": errors
    }


# ==========================================
# TRENDKÄLLA 3 – YOUTUBE API
# ==========================================

def get_youtube_api_popular():

    if not YOUTUBE_API_KEY:
        return []

    url = (
        "https://www.googleapis.com/youtube/v3/videos"
        "?part=snippet,statistics"
        "&chart=mostPopular"
        "&regionCode=SE"
        "&maxResults=20"
        f"&key={YOUTUBE_API_KEY}"
    )

    req = urllib.request.Request(
        url,
        headers={"User-Agent": "NOVA-Cloud/2.2"}
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        result = json.loads(
            response.read().decode("utf-8")
        )

    videos = []

    for video in result.get("items", []):

        snippet = video.get("snippet", {})
        statistics = video.get("statistics", {})
        video_id = video.get("id")

        videos.append({
            "title": snippet.get("title"),
            "channel": snippet.get("channelTitle"),
            "published": snippet.get("publishedAt"),
            "views": statistics.get("viewCount"),
            "likes": statistics.get("likeCount"),
            "url": (
                f"https://www.youtube.com/watch?v={video_id}"
                if video_id else None
            ),
            "source": "YouTube Data API",
            "statistics_available": True
        })

    return videos


def get_public_youtube_video_views(video_id):
    """Read a public view count; return None when unavailable."""
    if not video_id:
        return None
    url = "https://www.youtube.com/watch?v=" + quote(video_id)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0 Safari/537.36",
            "Accept-Language": "sv-SE,sv;q=0.9,en;q=0.8"
        }
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read(5000000).decode("utf-8", errors="replace")
        match = re.search(r'"viewCount"\s*:\s*"([0-9]+)"', html)
        if not match:
            match = re.search(r'"viewCount"\s*:\s*([0-9]+)', html)
        return int(match.group(1)) if match else None
    except Exception:
        return None


# ==========================================
# YOUTUBE – EGNA KANALERS ANALYS
# ==========================================

def get_youtube_channel_analytics():
    # Gratisläge: läs visningar från offentliga videosidor, aldrig gissa noll.
    if not YOUTUBE_API_KEY:
        rss_result = get_youtube_rss()
        recent_videos = rss_result.get("videos", [])[:10]
        channel_id = next(
            (item for item in YOUTUBE_CHANNEL_IDS
             if item.startswith("UC") and len(item) == 24),
            None
        )
        channel_title = (
            recent_videos[0].get("channel")
            if recent_videos else "Mikael Posth"
        )

        public_videos = []
        for video in recent_videos:
            views = get_public_youtube_video_views(video.get("video_id"))
            public_videos.append({
                "title": video.get("title", ""),
                "published": video.get("published"),
                "views": views,
                "likes": None,
                "comments": None,
                "url": video.get("url"),
                "source": "YouTube offentlig videosida" if views is not None else "Ej tillgänglig",
                "statistics_available": views is not None
            })

        views_found = sum(1 for video in public_videos if video.get("views") is not None)
        return {
            "status": "partial",
            "updated": datetime.now(timezone.utc).isoformat(),
            "source": "YouTube offentliga videosidor + RSS",
            "analytics_available": views_found > 0,
            "message": (
                f"Visningsantal kunde läsas för {views_found} av {len(public_videos)} "
                "senaste videor från offentliga YouTube-sidor. Kanalens totala "
                "visningar, prenumeranter, likes och kommentarer visas inte i "
                "gratisläget. YouTube kan begränsa automatiska hämtningar, "
                "så vissa värden kan saknas."
            ),
            "channels": [{
                "channel_id": channel_id,
                "title": channel_title or "Mikael Posth",
                "description": "",
                "published_at": None,
                "subscribers": None,
                "total_views": None,
                "video_count": None,
                "recent_videos": public_videos
            }],
            "channels_checked": rss_result.get("channels_checked", 0),
            "errors": rss_result.get("errors", [])
        }

    if not YOUTUBE_CHANNEL_IDS and not YOUTUBE_CHANNEL_HANDLE:
        raise HTTPException(
            status_code=503,
            detail="YOUTUBE_CHANNEL_HANDLE saknas i Render Environment."
        )

    channel_ids = resolve_youtube_channel_ids()

    if not channel_ids:
        raise HTTPException(
            status_code=404,
            detail=(
                "Kunde inte hitta YouTube-kanalen via handle "
                f"@{YOUTUBE_CHANNEL_HANDLE}. Kontrollera kanalnamnet "
                "och att YouTube Data API-nyckeln fungerar."
            )
        )

    if not channel_ids:
        raise HTTPException(
            status_code=400,
            detail="Inga giltiga YouTube-kanal-ID:n är konfigurerade."
        )

    def youtube_get(endpoint, params):
        query = "&".join(
            f"{quote(str(key))}={quote(str(value))}"
            for key, value in params.items()
        )
        url = f"https://www.googleapis.com/youtube/v3/{endpoint}?{query}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": f"NOVA-Cloud/{APP_VERSION}"}
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            details = error.read().decode("utf-8", errors="replace")
            raise ValueError(
                f"YouTube API {error.code}: {details[:900]}"
            )

    channel_result = youtube_get("channels", {
        "part": "snippet,statistics,contentDetails",
        "id": ",".join(channel_ids),
        "key": YOUTUBE_API_KEY
    })

    channels = []
    for item in channel_result.get("items", []):
        snippet = item.get("snippet", {})
        statistics = item.get("statistics", {})
        content = item.get("contentDetails", {})
        uploads_id = (
            content.get("relatedPlaylists", {}).get("uploads")
        )
        recent_videos = []

        if uploads_id:
            playlist = youtube_get("playlistItems", {
                "part": "snippet,contentDetails",
                "playlistId": uploads_id,
                "maxResults": 10,
                "key": YOUTUBE_API_KEY
            })
            video_ids = [
                entry.get("contentDetails", {}).get("videoId")
                for entry in playlist.get("items", [])
                if entry.get("contentDetails", {}).get("videoId")
            ]
            if video_ids:
                video_result = youtube_get("videos", {
                    "part": "snippet,statistics",
                    "id": ",".join(video_ids),
                    "key": YOUTUBE_API_KEY
                })
                for video in video_result.get("items", []):
                    video_snippet = video.get("snippet", {})
                    video_stats = video.get("statistics", {})
                    video_id = video.get("id")
                    recent_videos.append({
                        "title": video_snippet.get("title", ""),
                        "published": video_snippet.get("publishedAt"),
                        "views": int(video_stats.get("viewCount", 0)),
                        "likes": int(video_stats.get("likeCount", 0)),
                        "comments": int(video_stats.get("commentCount", 0)),
                        "url": f"https://www.youtube.com/watch?v={video_id}"
                    })

        recent_videos.sort(
            key=lambda video: video.get("published") or "",
            reverse=True
        )
        channels.append({
            "channel_id": item.get("id"),
            "title": snippet.get("title", "Okänd kanal"),
            "description": snippet.get("description", ""),
            "published_at": snippet.get("publishedAt"),
            "subscribers": (
                int(statistics.get("subscriberCount", 0))
                if not statistics.get("hiddenSubscriberCount")
                else None
            ),
            "total_views": int(statistics.get("viewCount", 0)),
            "video_count": int(statistics.get("videoCount", 0)),
            "recent_videos": recent_videos
        })

    if not channels:
        raise HTTPException(
            status_code=404,
            detail="YouTube hittade inga kanaler. Kontrollera kanal-ID:n."
        )

    return {
        "status": "completed",
        "updated": datetime.now(timezone.utc).isoformat(),
        "source": "YouTube Data API v3",
        "channels": channels
    }


@app.get("/api/youtube/analytics")
async def youtube_analytics():
    try:
        return get_youtube_channel_analytics()
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"Kunde inte hämta YouTube-statistik: {str(error)[:1200]}"
        )


# ==========================================
# SAMLAD TRENDMOTOR
# ==========================================

def collect_trends():

    data = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "google_trends": [],
        "youtube_rss": [],
        "youtube_popular": [],
        "youtube_channels_checked": 0,
        "sources": [],
        "errors": [],
        "limitations": [
            "YouTube RSS visar nya videor från valda kanaler.",
            "RSS innehåller inte visningsstatistik.",
            "Google Trends visar sökintresse, inte YouTube-visningar."
        ]
    }

    try:
        data["google_trends"] = get_google_trends()

        if data["google_trends"]:
            data["sources"].append("Google Trends Sverige")

    except Exception as error:
        data["errors"].append(
            "Google Trends: " + str(error)
        )

    rss_result = get_youtube_rss()

    data["youtube_rss"] = rss_result["videos"]
    data["youtube_channels_checked"] = (
        rss_result["channels_checked"]
    )

    data["errors"].extend(rss_result["errors"])

    if data["youtube_rss"]:
        data["sources"].append("YouTube RSS")

    elif not YOUTUBE_CHANNEL_IDS:
        data["errors"].append(
            "YouTube RSS väntar på YOUTUBE_API_KEY i Render för att slå upp @"
            + YOUTUBE_CHANNEL_HANDLE + "."
        )

    if YOUTUBE_API_KEY:
        try:
            data["youtube_popular"] = get_youtube_api_popular()

            if data["youtube_popular"]:
                data["sources"].append("YouTube Data API")

        except Exception as error:
            data["errors"].append(
                "YouTube Data API: " + str(error)
            )

    return data


# ==========================================
# HEMSIDA
# ==========================================

@app.get("/")
async def home():

    if not INDEX_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail="index.html kunde inte hittas."
        )

    return FileResponse(INDEX_FILE)


# ==========================================
# HÄLSOKONTROLL
# ==========================================

@app.get("/health")
async def health():

    return {
        "status": "online",
        "service": "NOVA Cloud",
        "version": APP_VERSION,
        "time": datetime.now(timezone.utc).isoformat()
    }


# ==========================================
# SYSTEMSTATUS
# ==========================================

@app.get("/api/status")
async def status():

    valid_channels = [
        item for item in YOUTUBE_CHANNEL_IDS
        if item.startswith("UC") and len(item) == 24
    ]
    channel_configured = bool(valid_channels or YOUTUBE_CHANNEL_HANDLE)

    return {
        "status": "online",
        "assistant": "JARVIS",
        "nova": "online",
        "jarvis": "online",
        "gemini_configured": bool(GEMINI_API_KEY),
        "openrouter_configured": bool(OPENROUTER_API_KEY),
        "youtube_api_configured": bool(YOUTUBE_API_KEY),
        "youtube_rss_configured": bool(
            valid_channels or (YOUTUBE_API_KEY and YOUTUBE_CHANNEL_HANDLE)
        ),
        "youtube_channels_configured": (
            len(valid_channels) if valid_channels else
            (1 if channel_configured and YOUTUBE_API_KEY else 0)
        ),
        "youtube_analytics_ready": bool(
            YOUTUBE_API_KEY and channel_configured
        ),
        "youtube_publish_ready": False,
        "youtube_channel_handle": "@mikaelposth",
        "youtube_channel_url": "https://www.youtube.com/@mikaelposth",
        "video_planner": "online",
        "video_renderer": "online",
        "version": APP_VERSION,
        "time": datetime.now(timezone.utc).isoformat()
    }


# ==========================================
# IDÉER – MIKAEL POSTH
# ==========================================

@app.get("/api/ideas")
async def ideas():

    return {
        "channel": "Mikael Posth",
        "ideas": [
            {
                "title": "Det här händer just nu",
                "description": "Aktuella ämnen och händelser med en personlig vinkel."
            },
            {
                "title": "Testar något nytt",
                "description": "Underhållning, tester och personliga utmaningar."
            },
            {
                "title": "En berättelse värd att dela",
                "description": "Intressanta historier och oväntade händelser."
            }
        ]
    }


# ==========================================
# TRENDMOTOR – HÄMTA DATA
# ==========================================

@app.get("/api/trends")
async def trends():

    data = collect_trends()

    has_data = (
        bool(data["google_trends"])
        or bool(data["youtube_rss"])
        or bool(data["youtube_popular"])
    )

    return {
        "assistant": "NOVA Trendmotor",
        "status": "completed" if has_data else "partial",
        "channel": "Mikael Posth",
        **data
    }


# ==========================================
# TRENDMOTOR – ANALYSERA OCH SKAPA IDÉER
# ==========================================

@app.post("/api/trends/ideas")
async def trend_ideas():

    data = collect_trends()

    has_data = (
        bool(data["google_trends"])
        or bool(data["youtube_rss"])
        or bool(data["youtube_popular"])
    )

    if not has_data:
        raise HTTPException(
            status_code=503,
            detail={
                "message": "Trendkällorna kunde inte hämtas.",
                "errors": data["errors"]
            }
        )

    trend_context = json.dumps(
        data,
        ensure_ascii=False,
        indent=2
    )

    message = f"""
Analysera följande insamlade trendmaterial.

KANAL: Mikael Posth

MATERIAL:
{trend_context}

UPPGIFT:
1. Identifiera intressanta ämnen.
2. Bedöm vilka som passar kanalen.
3. Skapa tre konkreta videoidéer.
4. Ge varje idé en stark videotitel.
5. Föreslå thumbnail och text på bilden.
6. Föreslå Short eller lång video.
7. Förklara varför idén kan fungera.
8. Rangordna idéerna efter potential.
9. Rekommendera vilken video som bör produceras först.
10. Föreslå en konkret öppning.

REGLER:
- Hitta inte på visningssiffror.
- Skilj fakta från bedömningar.
- RSS-videor är inte bevis på viralitet.
- Google Trends är sökintresse, inte YouTube-statistik.
- Ange tydligt om statistik saknas.
- Använd faktiska videolänkar när de finns.
- Anpassa för svensk YouTube-publik.
"""

    result = generate_reply(
        message,
        TREND_PROMPT
    )

    return {
        "assistant": "NOVA Trendmotor",
        "version": APP_VERSION,
        "status": "completed",
        "channel": "Mikael Posth",
        "updated": data["updated"],
        "sources": data["sources"],
        "errors": data["errors"],
        "data_quality": {
            "google_trends_items": len(data["google_trends"]),
            "youtube_rss_videos": len(data["youtube_rss"]),
            "youtube_api_videos": len(data["youtube_popular"]),
            "youtube_channels_checked": data["youtube_channels_checked"]
        },
        "limitations": data["limitations"],
        "engine": result["engine"],
        "analysis": result["reply"]
    }


# ==========================================
# NOVA VIDEO PRODUCER
# ==========================================

@app.post("/api/video/plan")
async def create_video_plan(request: VideoPlanRequest):

    user_prompt = f"""
SKAPA ETT KOMPLETT VIDEOPRODUKTIONSUNDERLAG.

KANAL: {request.channel}
VIDEOFORMAT: {request.format}
ÖNSKAD LÄNGD: {request.duration_minutes} minuter
STIL: {request.style}
MÅLGRUPP: {request.audience}

ANVÄNDARENS IDÉ:
{request.prompt}

REFERENSLÄNK:
{request.reference_url or "Ingen länk bifogad."}

REFERENSANALYS:
- Analysera bifogad referensbild visuellt: motiv, miljö, färger, ljus, komposition, stil och detaljer.
- Använd bilden som kreativ referens, inte som något som måste kopieras exakt.
- En videolänk är en referenslänk. Påstå inte att du har sett videoinnehållet om du inte faktiskt kan komma åt det.
- Om videoinnehållet inte är åtkomligt ska du utgå från användarens beskrivning och inte hitta på detaljer.
- Skapa en egen produktion för Mikael Posth och kopiera inte skyddat material bildruta för bildruta.

PRODUKTIONSKRAV:

- Skapa ett genomarbetat svenskt manus.
- Anpassa antalet scener till videons längd.
- Ge varje scen en tydlig bildprompt.
- Ge varje scen en separat videoprompt.
- Beskriv kamerarörelser.
- Föreslå ljud och musik.
- Skapa undertexter med tidsangivelser.
- Skapa en stark thumbnail-idé.
- Skapa YouTube-titel, beskrivning och sökord.
- Undvik upprepningar.
- Håll berättelsen sammanhängande.
- Gör materialet praktiskt att producera.

För en Short ska tempot vara högt.
För en lång video ska berättelsen utvecklas
med tydlig början, mitt och avslutning.

Returnera ett komplett produktionspaket
enligt JSON-strukturen i dina instruktioner.

VIKTIGT:
Returnera ett komplett JSON-objekt.
Avsluta samtliga strängar, listor och objekt.
Lämna inte JSON ofärdig.
"""

    reference_image_data = request.reference_image_data.strip()
    if reference_image_data and not reference_image_data.startswith("data:image/"):
        raise HTTPException(status_code=400, detail="Referensbilden har ett ogiltigt format.")
    if reference_image_data and len(reference_image_data) > 5600000:
        raise HTTPException(status_code=413, detail="Referensbilden är för stor. Max 4 MB.")

    result = generate_reply(
        user_prompt,
        VIDEO_PRODUCER_PROMPT,
        max_tokens=8192,
        json_mode=True,
        image_data=reference_image_data
    )

    try:
        try:
            plan = extract_json(result["reply"])

        except (ValueError, json.JSONDecodeError):
            plan = repair_video_json(result["reply"])

        plan = validate_video_plan(plan)

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "NOVA kunde inte skapa ett giltigt videopaket: "
                f"{str(error)}"
            )
        )

    try:
        subtitles_srt = create_srt(plan["subtitles"])

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "Videoplanen skapades men undertexterna "
                f"kunde inte byggas: {str(error)}"
            )
        )

    return {
        "assistant": "NOVA VIDEO PRODUCER",
        "status": "completed",
        "version": APP_VERSION,
        "created": datetime.now(timezone.utc).isoformat(),
        "channel": request.channel,
        "engine": result["engine"],
        "production_status": "script_ready",
        "render_status": "not_started",
        "video": plan,
        "subtitles_srt": subtitles_srt,
        "next_step": (
            "Produktionsunderlaget är klart. "
            "Videomotorn är ansluten. MP4-rendering finns via "
            "POST /api/video/render och kräver manus samt "
            "1–12 uppladdade scenbilder."
        )
    }


# ==========================================
# JARVIS AI
# ==========================================

@app.post("/api/chat")
async def chat(request: ChatRequest):

    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Meddelandet får inte vara tomt."
        )

    result = generate_reply(
        message,
        JARVIS_PROMPT
    )

    return {
        "assistant": "JARVIS",
        "status": "online",
        "engine": result["engine"],
        "reply": result["reply"]
    }


# ==========================================
# NOVA AI – YOUTUBE PRODUCENT
# ==========================================

WEBMASTER_PROMPT = """
Du är WEBMASTER, en senior webbdesigner och fullstackutvecklare.
Du arbetar ENDAST med att skapa och förbättra webbplatser åt användaren.

När användaren ber dig skapa en hemsida ska du leverera en komplett,
självständig HTML-sida i ETT enda kodblock märkt ```html.
Sidan ska innehålla all CSS och JavaScript inline och fungera direkt.
Skriv en kort sammanfattning före kodblocket. Använd en tydlig bildyta
med exakt token {{WEBMASTER_IMAGE}} som bildens src. Om ingen egen bild
finns ska sidan visa en neutral snygg platshållare.

Du hjälper till med:
- moderna, professionella och mobilanpassade hemsidor
- design, layout, färger, typografi och användarupplevelse
- HTML, CSS, JavaScript och vid behov React
- landningssidor, företagssidor, portfolios, butiker och bokningssidor
- formulär, menyer, undersidor och interaktiva funktioner
- SEO, tillgänglighet, prestanda och säkerhet
- felsökning och förbättring av befintliga webbplatser
- tydliga instruktioner för publicering och domänkoppling.

Arbeta praktiskt och stegvis. Fråga bara efter uppgifter som verkligen behövs.
När användaren ber om en hemsida ska du först förstå syfte och målgrupp,
föreslå en tydlig struktur och därefter skapa komplett, sammanhängande kod.
Om användaren ber om kod ska du ge kompletta filer när det är rimligt,
inte många små lösryckta kodfragment.

VIKTIGA REGLER:
- Hitta aldrig på att du har ändrat filer, publicerat en webbplats,
  köpt en domän eller anslutit en tjänst.
- Skilj mellan kod som är skapad, kod som är sparad och en webbplats
  som faktiskt är publicerad.
- Prioritera mobilanpassning, snabb laddning, säkerhet och tillgänglighet.
- Skriv naturlig svenska och förklara tekniska val kortfattat.
- Du arbetar inte med YouTube-produktion; det är NOVA:s uppgift.
"""


@app.post("/api/nova")
async def nova(request: NovaChatRequest):

    message = request.message.strip()
    reference_url = request.reference_url.strip()
    reference_image_data = request.reference_image_data.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Meddelandet får inte vara tomt."
        )

    if reference_url:
        message += (
            "\n\nREFERENSLÄNK FRÅN ANVÄNDAREN:\n"
            + reference_url
            + "\nBehandla länken som referens. Påstå inte att du har sett "
            "innehållet om det inte faktiskt är åtkomligt."
        )

    if reference_image_data:
        if not reference_image_data.startswith("data:image/"):
            raise HTTPException(
                status_code=400,
                detail="Referensbilden har ett ogiltigt format."
            )
        if len(reference_image_data) > 5600000:
            raise HTTPException(
                status_code=413,
                detail="Referensbilden är för stor. Max 4 MB."
            )

    try:
        result = generate_reply(
            message,
            NOVA_PROMPT,
            image_data=reference_image_data
        )
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=f"NOVA kunde inte behandla meddelandet: {str(error)[:1200]}"
        )

    return {
        "assistant": "NOVA",
        "status": "online",
        "engine": result["engine"],
        "reply": result["reply"],
        "reference_received": bool(reference_url or reference_image_data)
    }

@app.post("/api/webmaster/preview")
async def create_webmaster_preview(request: WebPreviewRequest):
    page_id = uuid.uuid4().hex[:12]
    preview_pages[page_id] = request.html
    return {
        "status": "ready",
        "preview_url": f"/preview/{page_id}",
        "note": "Tillfälliga förhandsvisningar rensas när Render startas om."
    }


@app.get("/preview/{page_id}", response_class=HTMLResponse)
async def view_webmaster_preview(page_id: str):
    page = preview_pages.get(page_id)
    if page is None:
        raise HTTPException(status_code=404, detail="Förhandsvisningen finns inte längre. Skapa en ny.")
    return HTMLResponse(
        content=page,
        headers={
            "Content-Security-Policy": "sandbox allow-scripts allow-forms allow-popups allow-modals; default-src https: data: blob: 'unsafe-inline' 'unsafe-eval'",
            "X-Content-Type-Options": "nosniff",
            "Referrer-Policy": "no-referrer"
        }
    )


@app.post("/api/webmaster")
async def webmaster(request: ChatRequest):
    message = request.message.strip()
    if not message:
        raise HTTPException(
            status_code=400,
            detail="Meddelandet får inte vara tomt."
        )
    result = generate_reply(
        message,
        WEBMASTER_PROMPT,
        max_tokens=8192
    )
    return {
        "assistant": "WEBMASTER",
        "status": "online",
        "engine": result["engine"],
        "reply": result["reply"]
    }

