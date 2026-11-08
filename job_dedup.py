"""Conservative duplicate detection for durable JARVIS jobs."""
import hashlib
import re
import unicodedata
from difflib import SequenceMatcher


_NUMBER_RE = re.compile(r"\d+(?:[.,]\d+)?")
_NEGATION_WORDS = {
    "inte", "ej", "aldrig", "inget", "ingen", "ingenting", "utan",
    "not", "never", "no", "without", "stoppa", "avbryt",
}


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
    Numeric identifiers and negation are treated as critical distinctions.
    """
    a = normalize_job_task(left)
    b = normalize_job_task(right)
    if not a or not b:
        return False

    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if min(len(tokens_a), len(tokens_b)) < 6:
        return False
    if a == b:
        return True

    # Never merge tasks that refer to different issue numbers, versions,
    # quantities, dates, or other explicit numeric identifiers.
    if set(_NUMBER_RE.findall(a)) != set(_NUMBER_RE.findall(b)):
        return False

    # A missing negation can reverse the requested action completely.
    negated_a = bool(tokens_a & _NEGATION_WORDS)
    negated_b = bool(tokens_b & _NEGATION_WORDS)
    if negated_a != negated_b:
        return False

    overlap = len(tokens_a & tokens_b) / min(len(tokens_a), len(tokens_b))
    ratio = SequenceMatcher(None, a, b, autojunk=False).ratio()
    return ratio >= 0.86 or (overlap >= 0.90 and ratio >= 0.78)
