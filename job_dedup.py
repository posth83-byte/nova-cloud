"""Conservative duplicate detection for durable JARVIS jobs."""
import hashlib
import re
import unicodedata
from difflib import SequenceMatcher


def normalize_job_task(value):
    """Normalize task wording while preserving meaningful words and numbers."""
    text = unicodedata.normalize("NFKC", str(value or "")).casefold()
    text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return " ".join(text.split())


def job_task_fingerprint(value):
    normalized = normalize_job_task(value)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def is_duplicate_job_task(left, right):
    """Match exact text or strongly overlapping substantial task descriptions.

    Short generic prompts are intentionally excluded from fuzzy matching to
    avoid merging unrelated requests such as 'continue' or 'test this'.
    """
    a = normalize_job_task(left)
    b = normalize_job_task(right)
    if not a or not b:
        return False
    if a == b:
        return True

    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if min(len(tokens_a), len(tokens_b)) < 6:
        return False

    overlap = len(tokens_a & tokens_b) / min(len(tokens_a), len(tokens_b))
    ratio = SequenceMatcher(None, a, b, autojunk=False).ratio()
    return ratio >= 0.86 or (overlap >= 0.90 and ratio >= 0.78)
