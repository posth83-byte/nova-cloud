import os
import json
import urllib.request
import urllib.error

from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel


app = FastAPI(
    title="NOVA Cloud",
    description="JARVIS och NOVA – personlig AI-central",
    version="1.4.0"
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

Du arbetar med YouTube-kanalerna:
- Skuggornas Arkiv
- Mikael Posth

Ditt uppdrag är att hjälpa till med:
- Trendanalys och videoidéer
- Research och faktakontroll
- Professionella videomanus
- Scenindelning och bildprompter
- Berättarröster och undertexter
- Videoproduktion
- Titlar, thumbnails och SEO
- Strategier för att utveckla YouTube-kanaler.

Du kommunicerar på naturlig svenska.

Du tänker kreativt, strategiskt och professionellt.
Du ger konkreta lösningar och arbetar stegvis.

När användaren ber om en video ska du hjälpa till
att utveckla hela produktionen från idé till färdigt
publiceringsmaterial.

Hitta aldrig på fakta eller påstå att du har
producerat eller publicerat något som du inte gjort.
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
        "version": "1.4.0",
        "time": datetime.now().isoformat()
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
        "version": "1.4.0",
        "time": datetime.now().isoformat()
    }


# ==========================================
# IDÉER
# ==========================================

@app.get("/api/ideas")
async def ideas():

    return {
        "ideas": [
            {
                "title": "Skuggornas Arkiv",
                "description": "Mystiska berättelser och oförklarliga händelser."
            },
            {
                "title": "Mikael Posth",
                "description": "Musik, underhållning och personliga videor."
            },
            {
                "title": "NOVA Produktion",
                "description": "Nya idéer, manus och videoprojekt."
            }
        ]
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