
from fastapi import FastAPI
from fastapi.responses import FileResponse
from datetime import datetime, timezone
from pathlib import Path

app = FastAPI(
    title="NOVA Cloud",
    description="JARVIS & NOVA AI Command Center",
    version="1.1.0"
)

BASE_DIR = Path(__file__).resolve().parent
DASHBOARD = BASE_DIR / "index.html"


@app.get("/")
def home():
    if DASHBOARD.exists():
        return FileResponse(DASHBOARD)

    return {
        "assistant": "NOVA",
        "status": "online",
        "message": "NOVA Cloud är igång!",
        "version": "1.1.0"
    }


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
            "ai_brain": "planned",
            "jarvis_assistant": "online",
            "command_center": "online"
        }
    }


@app.get("/api/ideas")
def ideas():
    return {
        "message": "NOVA är redo att ta emot trendanalys.",
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
