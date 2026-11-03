
import os
import json
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel


app = FastAPI(
    title="NOVA Cloud",
    description="JARVIS och NOVA – personlig AI-central",
    version="1.5.0"
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

Du ska undersöka olika innehållsområden.
Lås dig inte vid en enda genre.

Prioritera idéer som har potential att:
- Fånga tittarens uppmärksamhet snabbt.
- Skapa engagemang och kommentarer.
- Fungera både som Shorts och längre videor.
- Vara rimliga att producera med gratisverktyg.

När trenddata finns tillgänglig ska du använda den.
Skilj mellan verifierade uppgifter och egna
bedömningar. Hitta aldrig på statistik.

Du kommunicerar på naturlig svenska.

När användaren ber om en video ska du hjälpa till
att utveckla hela produktionen från idé till
färdigt publiceringsmaterial.

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
        result = json.loads(
            response.read().decode("utf-8")
        )

    candidates = result.get("candidates", [])

    if not candidates:
        raise ValueError("Gemini skickade inget svar.")

    parts = candidates[0].get(
        "content", {}
    ).get("parts", [])

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
        result = json.loads(
            response.read().decode("utf-8")
        )

    choices = result.get("choices", [])

    if not choices:
        raise ValueError("OpenRouter skickade inget svar.")

    answer = (
        choices[0]
        .get("message", {})
        .get("content", "")
    )

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
            answer = ask_gemini(message, system_prompt)

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
            answer = ask_openrouter(message, system_prompt)

            return {
                "reply": answer,
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
            "User-Agent": "Mozilla/5.0 NOVA-Cloud/1.5"
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
# TRENDKÄLLA 2 – YOUTUBE POPULÄRA VIDEOR
# ==========================================

def get_youtube_popular():

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
            "User-Agent": "NOVA-Cloud/1.5"
        }
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
            "source": "YouTube Data API"
        })

    return videos


# ==========================================
# SAMLAD TRENDMOTOR
# ==========================================

def collect_trends():

    data = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "google_trends": [],
        "youtube_popular": [],
        "sources": [],
        "errors": []
    }

    try:
        data["google_trends"] = get_google_trends()
        data["sources"].append("Google Trends Sverige")

    except Exception as error:
        data["errors"].append(
            "Google Trends: " + str(error)
        )

    try:
        data["youtube_popular"] = get_youtube_popular()

        if YOUTUBE_API_KEY:
            data["sources"].append("YouTube Data API")
        else:
            data["errors"].append(
                "YouTube Data API är inte konfigurerat."
            )

    except Exception as error:
        data["errors"].append(
            "YouTube: " + str(error)
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
        "version": "1.5.0",
        "time": datetime.now(timezone.utc).isoformat()
    }


# ==========================================
# SYSTEMSTATUS
# ==========================================

@app.get("/api/status")
async def status():

    return {
        "status": "online",
        "assistant": "JARVIS",
        "nova": "online",
        "jarvis": "online",
        "gemini_configured": bool(GEMINI_API_KEY),
        "openrouter_configured": bool(OPENROUTER_API_KEY),
        "youtube_api_configured": bool(YOUTUBE_API_KEY),
        "version": "1.5.0",
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

    return {
        "assistant": "NOVA Trendmotor",
        "status": "completed",
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
Analysera följande aktuella trendmaterial.

KANAL: Mikael Posth

MATERIAL:
{trend_context}

Uppgift:

1. Identifiera de mest intressanta ämnena.
2. Bedöm vilka som passar Mikael Posth.
3. Skapa tre konkreta videoidéer.
4. Ge varje idé en stark videotitel.
5. Föreslå thumbnail och kort text på bilden.
6. Föreslå om videon bör vara en Short eller lång video.
7. Förklara varför idén kan fungera.
8. Rangordna idéerna efter potential.
9. Föreslå vilken video som bör produceras först.

VIKTIGT:

- Hitta inte på visningssiffror eller statistik.
- Skilj mellan faktiska trenddata och egna bedömningar.
- Populära videor är inte automatiskt växande trender.
- Anpassa idéerna till en svensk YouTube-publik.
- Tänk kreativt och våga föreslå olika ämnen.
- Prioritera idéer som går att producera med gratisverktyg.
"""

    result = generate_reply(
        message,
        NOVA_PROMPT
    )

    return {
        "assistant": "NOVA Trendmotor",
        "status": "completed",
        "channel": "Mikael Posth",
        "updated": data["updated"],
        "sources": data["sources"],
        "errors": data["errors"],
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
