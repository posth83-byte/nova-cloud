
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json
import os

app = FastAPI(
    title="NOVA Cloud",
    description="JARVIS & NOVA AI Command Center",
    version="1.2.0"
)

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD = BASE_DIR / "index.html"

GEMINI_MODEL = "gemini-3.8-flash"


class ChatRequest(BaseModel):
    message: str


@app.get("/")
def home():
    if DASHBOARD.exists():
        return FileResponse(DASHBOARD)

    return {"assistant": "NOVA", "status": "online"}


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "time": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/status")
def status():
    return {
        "name": "NOVA",
        "status": "online",
        "modules": {
            "trend_scanner": "planned",
            "youtube_analyst": "planned",
            "video_producer": "planned",
            "ai_brain": "online",
            "jarvis_assistant": "online",
            "command_center": "online"
        }
    }


@app.get("/api/ideas")
def ideas():
    return {
        "message": "NOVA är redo för trendanalys.",
        "categories": [
            "Musik",
            "Underhållning",
            "Gaming",
            "Mystik",
            "Dokumentärer",
            "Fakta",
            "Humor",
            "Berättelser"
        ]
    }


@app.post("/api/chat")
def chat(request: ChatRequest):

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="JARVIS AI-nyckel saknas i servern."
        )

    message = request.message.strip()

    if not message:
        raise HTTPException(
            status_code=400,
            detail="Skriv eller säg något först."
        )

    if len(message) > 4000:
        raise HTTPException(
            status_code=400,
            detail="Meddelandet är för långt."
        )

    payload = {
        "system_instruction": {
            "parts": [{
                "text": (
                    "Du är JARVIS, en intelligent och personlig "
                    "AI-assistent. Du kommunicerar naturligt på "
                    "svenska med lugn, tydlig och professionell ton. "
                    "Du är hjälpsam, analytisk och lösningsorienterad. "
                    "Du hjälper användaren med teknik, vardag, "
                    "planering och projekt. Kalla dig JARVIS. "
                    "Hitta aldrig på att du har utfört handlingar "
                    "som du inte faktiskt har utfört."
                )
            }]
        },
        "contents": [{
            "role": "user",
            "parts": [{"text": message}]
        }],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 800
        }
    }

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"models/{GEMINI_MODEL}:generateContent"
    )

    req = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        },
        method="POST"
    )

    try:
        with urlopen(req, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))

        candidates = result.get("candidates", [])

        if not candidates:
            raise HTTPException(
                status_code=502,
                detail="AI:n gav inget svar."
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
                detail="AI:n returnerade ett tomt svar."
            )

        return {
            "assistant": "JARVIS",
            "status": "online",
            "reply": answer
        }

    except HTTPError as error:
        raise HTTPException(
            status_code=502,
            detail=f"Gemini API svarade med felkod {error.code}."
        )

    except (URLError, TimeoutError):
        raise HTTPException(
            status_code=503,
            detail="Kunde inte nå JARVIS AI just nu."
        )
