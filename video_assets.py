"""Free, attribution-aware visual assets from Wikimedia Commons.

Only images with an explicit Creative Commons or public-domain license are
accepted. Network failures are non-fatal: the renderer falls back to original
procedural artwork.
"""
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

from PIL import Image

API = "https://commons.wikimedia.org/w/api.php"
USER_AGENT = "NOVACloudVideoStudio/1.0 (free educational video renderer)"
MAX_IMAGE_BYTES = 12 * 1024 * 1024
ALLOWED_LICENSE = re.compile(r"^(?:CC0|Public domain|CC BY(?:-SA)?(?: 2\.0| 3\.0| 4\.0)?)$", re.I)


def _request_json(params):
    url = API + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=12) as response:
        payload = response.read(2_000_000)
    return json.loads(payload.decode("utf-8"))


def search_commons_images(query, limit=5):
    """Return licensed Commons image metadata, never unlicensed/unknown assets."""
    clean = re.sub(r"[^\w\såäöÅÄÖ-]", " ", str(query or ""), flags=re.UNICODE)
    clean = " ".join(clean.split())[:180]
    if not clean:
        return []
    try:
        data = _request_json({
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": f"{clean} filetype:bitmap",
            "gsrnamespace": 6,
            "gsrlimit": max(1, min(int(limit) * 3, 15)),
            "prop": "imageinfo",
            "iiprop": "url|extmetadata",
            "iiurlwidth": 1280,
        })
        pages = (data.get("query") or {}).get("pages") or {}
        results = []
        for page in pages.values():
            info = (page.get("imageinfo") or [{}])[0]
            meta = info.get("extmetadata") or {}
            license_name = (meta.get("LicenseShortName") or {}).get("value", "")
            if not ALLOWED_LICENSE.search(re.sub("<[^>]+>", "", license_name)):
                continue
            image_url = info.get("thumburl") or info.get("url")
            if not image_url or not image_url.startswith("https://"):
                continue
            results.append({
                "title": re.sub("<[^>]+>", "", page.get("title", ""))[:240],
                "image_url": image_url,
                "page_url": info.get("descriptionurl", ""),
                "license": re.sub("<[^>]+>", "", license_name)[:100],
                "license_url": re.sub("<[^>]+>", "", (meta.get("LicenseUrl") or {}).get("value", ""))[:500],
                "artist": re.sub("<[^>]+>", "", (meta.get("Artist") or {}).get("value", ""))[:500],
                "credit": re.sub("<[^>]+>", "", (meta.get("Credit") or {}).get("value", ""))[:500],
            })
            if len(results) >= limit:
                break
        return results
    except Exception:
        return []


def download_commons_image(asset, destination):
    """Download and validate one Commons image; return False on any failure."""
    destination = Path(destination)
    request = urllib.request.Request(asset["image_url"], headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=18) as response:
            content_type = (response.headers.get("Content-Type") or "").lower()
            if not content_type.startswith("image/"):
                return False
            data = response.read(MAX_IMAGE_BYTES + 1)
        if not data or len(data) > MAX_IMAGE_BYTES:
            return False
        destination.write_bytes(data)
        with Image.open(destination) as image:
            image.verify()
        return True
    except Exception:
        destination.unlink(missing_ok=True)
        return False
