import os
import json
import re
import urllib.request
import xml.etree.ElementTree as ET

from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field


app = FastAPI(
    title="NOVA Cloud",
    description="JARVIS och NOVA – personlig AI-central",
    version="2.1.0"
)


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

YOUTUBE_CHANNEL_IDS = [
    item.strip()
    for item in os.getenv(
        "YOUTUBE_CHANNEL_IDS", ""
    ).replace(";", ",").split(",")
    if item.strip()
]

MAX_RSS_CHANNELS = 15
MAX_RSS_VIDEOS = 60


# ==========================================
# MODELLER
# ==========================================

class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)


class VideoPlanRequest(BaseModel):
    prompt: str = Field(min_length=5, max_length=5000)
    channel: str = "Mikael Posth"
    format: str = "long"
    duration_minutes: int = Field(default=5, ge=1, le=30)
    style: str = "Engagerande och professionell"
    audience: str = "Svensk YouTube-publik"


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

Du utvecklar YouTube-kanalerna:
- Mikael Posth
- Skuggornas Arkiv

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

def ask_gemini(message, system_prompt, max_tokens=2048):

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{GEMINI_MODEL}:generateContent"
    )

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {
                "role": "user",
                "parts": [{"text": message}]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": max_tokens
        }
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

    with urllib.request.urlopen(req, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))

    candidates = result.get("candidates", [])

    if not candidates:
        raise ValueError("Gemini skickade inget svar.")

    parts = candidates[0].get("content", {}).get("parts", [])

    answer = " ".join(
        part.get("text", "")
        for part in parts
        if part.get("text")
    ).strip()

    if not answer:
        raise ValueError("Gemini skickade ett tomt svar.")

    return answer


# ==========================================
# OPENROUTER RESERVMOTOR
# ==========================================

def ask_openrouter(message, system_prompt, max_tokens=2048):

    url = "https://openrouter.ai/api/v1/chat/completions"

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message}
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens
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

    with urllib.request.urlopen(req, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))

    choices = result.get("choices", [])

    if not choices:
        raise ValueError("OpenRouter skickade inget svar.")

    answer = choices[0].get("message", {}).get("content", "")

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

def generate_reply(message, system_prompt, max_tokens=2048):

    gemini_error = None

    if GEMINI_API_KEY:
        try:
            return {
                "reply": ask_gemini(
                    message,
                    system_prompt,
                    max_tokens
                ),
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
                    max_tokens
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

    cleaned = text.strip()

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE
    )

    cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1:
        raise ValueError("AI-svaret innehöll ingen giltig JSON.")

    return json.loads(cleaned[start:end + 1])


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

    for key in required:
        if key not in plan:
            raise ValueError(
                f"Videoplanen saknar fältet: {key}"
            )

    if not isinstance(plan["scenes"], list) or not plan["scenes"]:
        raise ValueError("Videoplanen saknar scener.")

    if not isinstance(plan["subtitles"], list):
        raise ValueError("Undertexterna har fel format.")

    for scene in plan["scenes"]:

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

    return plan


# ==========================================
# TRENDKÄLLA 1 – GOOGLE TRENDS
# ==========================================

def get_google_trends():

    url = "https://trends.google.com/trending/rss?geo=SE"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 NOVA-Cloud/2.1"
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

    valid_ids = [
        channel_id
        for channel_id in YOUTUBE_CHANNEL_IDS
        if channel_id.startswith("UC") and len(channel_id) == 24
    ]

    invalid_count = len(YOUTUBE_CHANNEL_IDS) - len(valid_ids)

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
                    "User-Agent": "Mozilla/5.0 NOVA-Cloud/2.1"
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
        headers={"User-Agent": "NOVA-Cloud/2.1"}
    )

    with urllib.request.urlopen(req, timeout=20) as response:
        result = json.loads(response.read().decode("utf-8"))

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
            "YouTube RSS väntar på kanal-ID:n i Render."
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
        "version": "2.1.0",
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

    return {
        "status": "online",
        "assistant": "JARVIS",
        "nova": "online",
        "jarvis": "online",
        "gemini_configured": bool(GEMINI_API_KEY),
        "openrouter_configured": bool(OPENROUTER_API_KEY),
        "youtube_api_configured": bool(YOUTUBE_API_KEY),
        "youtube_rss_configured": bool(valid_channels),
        "youtube_channels_configured": len(valid_channels),
        "video_planner": "online",
        "video_renderer": "not_configured",
        "version": "2.1.0",
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
        "version": "2.1.0",
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
# NYHET: NOVA VIDEO PRODUCER
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
"""

    result = generate_reply(
        user_prompt,
        VIDEO_PRODUCER_PROMPT,
        max_tokens=8192
    )

    try:
        plan = extract_json(result["reply"])
        plan = validate_video_plan(plan)

    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail=(
                "NOVA kunde inte skapa ett giltigt "
                f"videopaket: {str(error)}"
            )
        )

    subtitles_srt = create_srt(plan["subtitles"])

    return {
        "assistant": "NOVA VIDEO PRODUCER",
        "status": "completed",
        "version": "2.1.0",
        "created": datetime.now(timezone.utc).isoformat(),
        "channel": request.channel,
        "engine": result["engine"],
        "production_status": "script_ready",
        "render_status": "not_started",
        "video": plan,
        "subtitles_srt": subtitles_srt,
        "next_step": (
            "Produktionsunderlaget är klart. "
            "Videoklipp, berättarröst och slutlig "
            "MP4-rendering kräver en ansluten "
            "videoproduktionsmotor."
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

@app.post("/api/nova")
async def nova(request: ChatRequest):

    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Meddelandet får inte vara tomt."
        )

    result = generate_reply(
        message,
        NOVA_PROMPT
    )

    return {
        "assistant": "NOVA",
        "status": "online",
        "engine": result["engine"],
        "reply": result["reply"]
    }