
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
    version="1.3.0"
)


# ==========================================
# INSTÄLLNINGAR
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
INDEX_FILE = BASE_DIR / "index.html"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")


# ==========================================
# MODELLER
# ==========================================

class ChatRequest(BaseModel):
    message: str


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
# JARVIS AI – GEMINI
# ==========================================

@app.post("/api/chat")
async def chat(request: ChatRequest):

    if not GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="JARVIS AI-nyckel saknas i servern."
        )

    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Meddelandet får inte vara tomt."
        )

    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{GEMINI_MODEL}:generateContent"
    )

    system_instruction = """
Du är JARVIS, en avancerad personlig AI-assistent.

Du kommunicerar alltid på naturlig svenska om användaren
inte ber om ett annat språk.

Du är lugn, intelligent, professionell, vänlig,
analytisk och lösningsorienterad.

Du hjälper användaren med teknik, vardag, planering,
research och personliga projekt.

Du samarbetar med NOVA, som ansvarar för kreativ
produktion och YouTube-projekt.

Du ska ge tydliga och praktiska svar.
Undvik onödigt långa förklaringar.
Ta ett steg i taget när användaren behöver hjälp.
"""

    payload = {
        "system_instruction": {
            "parts": [
                {
                    "text": system_instruction
                }
            ]
        },
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": message
                    }
                ]
            }
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 2048
        }
    }

    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))

        candidates = result.get("candidates", [])

        if not candidates:
            raise HTTPException(
                status_code=502,
                detail="Gemini skickade inget svar."
            )

        parts = candidates[0].get("content", {}).get("parts", [])

        answer = " ".join(
            part.get("text", "")
            for part in parts
            if part.get("text")
        ).strip()

        if not answer:
            raise HTTPException(
                status_code=502,
                detail="JARVIS fick ett tomt svar från Gemini."
            )

        return {
            "assistant": "JARVIS",
            "status": "online",
            "reply": answer
        }

    except urllib.error.HTTPError as error:
        error_body = error.read().decode(
            "utf-8",
            errors="replace"
        )

        raise HTTPException(
            status_code=502,
            detail=f"Gemini API fel {error.code}: {error_body}"
        )

    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=503,
            detail=f"Kunde inte nå Gemini: {error.reason}"
        )

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Internt JARVIS-fel: {str(error)}"
        )
