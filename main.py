
from fastapi import FastAPI
from datetime import datetime, timezone

app = FastAPI(
    title="NOVA Cloud",
    description="NOVA AI YouTube Intelligence",
    version="1.0.0"
)

@app.get("/")
def home():
    return {
        "assistant": "NOVA",
        "status": "online",
        "message": "NOVA Cloud är igång!",
        "version": "1.0.0"
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
            "ai_brain": "planned"
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
