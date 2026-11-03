
import os
import json
import urllib.request
import xml.etree.ElementTree as ET

from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel


app = FastAPI(
    title="NOVA Cloud",
    description="JARVIS och NOVA – personlig AI-central",
    version="2.0.0"
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

# Lägg kanalernas UC-ID:n här via Render Environment.
# Flera ID:n separeras med kommatecken.
YOUTUBE_CHANNEL_IDS = [
    item.strip()
    for item in os.getenv("YOUTUBE_CHANNEL_IDS", "").replace(";", ",").split(",")
    if item.strip()
]

MAX_RSS_CHANNELS = 15
MAX_RSS_VIDEOS = 60


# ==========================================
# MODELLER
# ==========================================

class ChatRequest(BaseModel):
    message: str


# ==========================================
# AI-PERSONLIGHETER
# ==========================================

JARVIS_PROMPT = """
Du är JARVIS, en avancerad personlig AI-assistent.

Du kommunicerar alltid på naturlig svenska om
användaren inte ber om ett annat språk.

Du är lugn, intelligent, professionell, vänlig,
analytisk och lösningsorienterad.

Du hjälper användaren med teknik, vardag,
planering, research och personliga projekt.

Du samarbetar med NOVA, som ansvarar för
kreativ produktion och YouTube-projekt.

Du ska ge tydliga och praktiska svar.
Undvik onödigt långa förklaringar.
Ta ett steg i taget när användaren behöver hjälp.
"""

NOVA_PROMPT = """
Du är NOVA, en avancerad kreativ AI-producent.

Ditt huvudsakliga uppdrag är att utveckla
YouTube-kanalen Mikael Posth.

Du ansvarar för:
- Trendanalys och videoidéer
- Research och faktakontroll
- Professionella videomanus
- Scenindelning och bildprompter
- Berättarröster och undertexter
- Videoproduktion
- Titlar, thumbnails och SEO
- Analys av vad som fungerar på YouTube
- Strategier för att utveckla kanalen.

Undersök olika innehållsområden.
Lås dig inte vid en enda genre.

Prioritera idéer som kan:
- Fånga tittarens uppmärksamhet snabbt.
- Skapa engagemang och kommentarer.
- Fungera som Shorts eller längre videor.
- Produceras med gratisverktyg.

När trenddata finns tillgänglig ska du använda den.

VIKTIGA REGLER:
- Skilj verifierade uppgifter från bedömningar.
- Hitta aldrig på statistik eller visningar.
- RSS-publicering betyder inte att en video är viral.
- En populär video är inte automatiskt en växande trend.
- Ange när data saknas.
- Hitta inte på källor.

Du kommunicerar på naturlig svenska.

När användaren ber om en video ska du hjälpa till
med hela produktionen från idé till publiceringsmaterial.

Påstå aldrig att du har producerat eller publicerat
något som du inte faktiskt har gjort.
"""


# ==========================================
# GEMINI MOTOR
# ==========================================

def ask_gemini(message, system_prompt):

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
            "maxOutputTokens": 2048
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

    with urllib.request.urlopen(req, timeout=60) as response:
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

def ask_openrouter(message, system_prompt):

    url = "https://openrouter.ai/api/v1/chat/completions"

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": system_prompt
            },
            {
                "role": "user",
                "content": message
            }
        ],
        "temperature": 0.7,
        "max_tokens": 2048
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

    with urllib.request.urlopen(req, timeout=60) as response:
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

def generate_reply(message, system_prompt):

    gemini_error = None

    if GEMINI_API_KEY:
        try:
            return {
                "reply": ask_gemini(message, system_prompt),
                "engine": "Gemini"
            }
        except Exception as error:
            gemini_error = str(error)
    else:
        gemini_error = "Gemini API-nyckel saknas."

    if OPENROUTER_API_KEY:
        try:
            return {
                "reply": ask_openrouter(message, system_prompt),
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
# TRENDKÄLLA 1 – GOOGLE TRENDS
# ==========================================

def get_google_trends():

    url = "https://trends.google.com/trending/rss?geo=SE"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 NOVA-Cloud/2.0"
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

    # YouTube kräver kanal-ID för sina officiella RSS-flöden.
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
                    "User-Agent": "Mozilla/5.0 NOVA-Cloud/2.0"
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

                video_id = entry.findtext("yt:videoId", namespaces=ns)
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

    # Ta bort eventuella dubbletter.
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
# TRENDKÄLLA 3 – YOUTUBE API (VALFRI)
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
        headers={
            "User-Agent": "NOVA-Cloud/2.0"
        }
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

    # Google Trends
    try:
        data["google_trends"] = get_google_trends()

        if data["google_trends"]:
            data["sources"].append("Google Trends Sverige")

    except Exception as error:
        data["errors"].append(
            "Google Trends: " + str(error)
        )

    # YouTube RSS
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

    # Valfri YouTube API
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
        "version": "2.0.0",
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
        "version": "2.0.0",
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

1. Identifiera de mest intressanta ämnena.
2. Bedöm vilka som passar Mikael Posth.
3. Skapa tre konkreta videoidéer.
4. Ge varje idé en stark videotitel.
5. Föreslå thumbnail och text på bilden.
6. Föreslå Short eller lång video.
7. Förklara varför idén kan fungera.
8. Rangordna idéerna efter potential.
9. Rekommendera vilken video som bör produceras först.
10. Föreslå en konkret öppning som fångar tittaren.

REGLER:

- Hitta inte på visningssiffror.
- Skilj mellan fakta och egna bedömningar.
- RSS-videor är publicerade videor, inte bevis på viralitet.
- Google Trends är sökintresse, inte YouTube-statistik.
- Ange tydligt om statistik saknas.
- Använd faktiska videolänkar när de finns.
- Anpassa för en svensk YouTube-publik.
- Tänk kreativt och föreslå olika ämnen.
- Prioritera gratisverktyg och rimlig produktionstid.
"""

    result = generate_reply(
        message,
        NOVA_PROMPT
    )

    return {
        "assistant": "NOVA Trendmotor",
        "version": "2.0.0",
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
