"""Free, source-linked factual research using Wikipedia's public MediaWiki API.

This is a starting source for explainers, not a substitute for fact checking.
"""
import re
import urllib.parse
import urllib.request

USER_AGENT = "NOVACloudVideoStudio/1.0 (factual video research)"
LANGUAGES = ("sv", "en")


def _api(language, params):
    base = f"https://{language}.wikipedia.org/w/api.php"
    url = base + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=15) as response:
        return response.read(2_500_000).decode("utf-8")


def research_wikipedia(topic):
    """Find a relevant article and return a clean extract with its source URL."""
    query = " ".join(str(topic or "").split())[:180]
    if not query:
        return None
    import json
    for language in LANGUAGES:
        try:
            search_data = json.loads(_api(language, {
                "action": "query", "list": "search", "srsearch": query,
                "srlimit": 3, "format": "json", "utf8": 1,
            }))
            hits = (search_data.get("query") or {}).get("search") or []
            if not hits:
                continue
            title = hits[0].get("title", "").strip()
            if not title:
                continue
            article_data = json.loads(_api(language, {
                "action": "query", "prop": "extracts", "explaintext": 1,
                "exchars": 9000, "titles": title, "format": "json",
            }))
            pages = (article_data.get("query") or {}).get("pages") or {}
            extract = next((page.get("extract", "") for page in pages.values()), "")
            extract = re.sub(r"\s+", " ", extract).strip()
            sentences = [
                item.strip() for item in re.split(r"(?<=[.!?])\s+", extract)
                if len(item.strip()) >= 35
            ]
            if len(sentences) < 5:
                continue
            return {
                "title": title,
                "language": language,
                "source": "Wikipedia",
                "source_url": f"https://{language}.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}",
                "extract": extract[:9000],
                "sentences": sentences[:30],
            }
        except Exception:
            continue
    return None


def build_explainer_beats(research, duration_mode="standard"):
    """Turn each selected sourced sentence into its own editable scene."""
    if not research:
        return []
    limits = {"short": 10, "standard": 20, "long": 30}
    if duration_mode not in limits:
        return []
    sentences = research.get("sentences") or []
    if len(sentences) < 5:
        return []
    selected = sentences[:limits[duration_mode]]
    beats = []
    kinds = ("generic", "work", "phone", "money", "sleep", "gym", "food", "love", "phone", "generic")
    for index, sentence in enumerate(selected):
        line = re.sub(r"\\s+", " ", str(sentence)).strip()
        if len(line) > 420:
            clipped = line[:417]
            boundary = clipped.rfind(" ")
            line = clipped[:boundary if boundary > 250 else 417].rstrip(" ,;:") + "…"
        caption = line
        if len(caption) > 115:
            caption = caption[:112].rsplit(" ", 1)[0] + "…"
        beats.append((f"FAKTA {index + 1}", line, caption, kinds[index % len(kinds)]))
    return beats
