"""
Базовый парсер — общие утилиты для всех парсеров.
"""
import hashlib
import re
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


def make_uid(*parts) -> str:
    """Create a stable unique ID from string parts."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()


def clean_html(text: str) -> str:
    """Strip HTML tags from text."""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def matches_categories(text: str, categories: list, lang: str = "ru") -> bool:
    """
    Return True if text contains keywords for any of the given categories.
    If categories list is empty — accept everything.
    """
    if not categories:
        return True

    if lang == "ru":
        from data.categories import KEYWORDS_RU as KW
    else:
        from data.categories import KEYWORDS_EN as KW

    text_lower = text.lower()
    for cat in categories:
        for kw in KW.get(cat, []):
            if kw.lower() in text_lower:
                return True
    return False


def normalize_date(dt_str: str) -> str:
    """Try to parse and normalize a date string."""
    if not dt_str:
        return datetime.now().strftime("%d.%m.%Y %H:%M")
    for fmt in ("%a, %d %b %Y %H:%M:%S %z",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S",
                "%d.%m.%Y %H:%M"):
        try:
            return datetime.strptime(dt_str[:25], fmt).strftime("%d.%m.%Y %H:%M")
        except Exception:
            pass
    return dt_str[:19]


def get_http_timeout(default: float = 8.0) -> float:
    """HTTP timeout from env. Keeps UI responsive when a source is slow/down."""
    raw = os.environ.get("HTTP_TIMEOUT_SECONDS", str(default))
    try:
        value = float(raw)
    except ValueError:
        value = default
    return max(1.0, min(value, 30.0))
