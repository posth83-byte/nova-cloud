"""Cost guard for optional paid video-generation providers.

The free procedural renderer is the default. External paid providers are
blocked unless an operator explicitly enables them in the server environment.
"""
import os


def paid_video_engines_enabled() -> bool:
    value = os.getenv("ENABLE_PAID_VIDEO_ENGINES", "false").strip().casefold()
    return value in {"1", "true", "yes", "on"}
