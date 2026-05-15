"""VK-only parser: reads public VK group walls through VK API and extracts order-like posts."""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Dict, Iterable, List, Optional

import requests

from parsers.base import clean_html, make_uid, matches_categories, normalize_date, get_http_timeout

logger = logging.getLogger(__name__)

VK_API_URL = "https://api.vk.com/method/"
VK_API_VERSION = os.environ.get("VK_API_VERSION", "5.131")
DEFAULT_COUNT = int(os.environ.get("VK_POSTS_PER_GROUP", "30"))
ORDER_KEYWORDS = [
    "нужно", "нужен", "нужна", "требуется", "ищем", "ищу", "заказ", "проект",
    "задача", "доработать", "разработать", "сделать", "написать", "бот", "парсер",
    "сайт", "лендинг", "интеграция", "оплата", "api", "бюджет", "₽", "руб",
]

_vk_token: str = ""


def set_vk_token(token: Optional[str]) -> None:
    global _vk_token
    _vk_token = (token or "").strip()


def get_vk_token() -> str:
    token = (
        _vk_token
        or os.environ.get("VK_PARSER_TOKEN", "")
        or os.environ.get("VK_SERVICE_TOKEN", "")
        or os.environ.get("VK_TOKEN", "")
    )
    return token.strip()


def vk_api_call(method: str, params: Dict[str, Any], token: Optional[str] = None) -> Dict[str, Any]:
    token = (token or get_vk_token()).strip()
    if not token or token.startswith("YOUR_"):
        raise RuntimeError("VK_TOKEN не задан. Укажи сервисный ключ VK в .env")

    request_params = dict(params)
    request_params["access_token"] = token
    request_params["v"] = VK_API_VERSION

    response = requests.get(VK_API_URL + method, params=request_params, timeout=get_http_timeout(8))
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        error = payload["error"]
        raise RuntimeError(f"VK API error {error.get('error_code')}: {error.get('error_msg')}")
    return payload


def normalize_group(group: Any) -> Dict[str, str]:
    if isinstance(group, str):
        domain = group.strip().replace("https://vk.com/", "").replace("vk.com/", "").strip("/")
        return {"domain": domain, "title": domain, "lang": "ru"}
    if isinstance(group, dict):
        domain = str(group.get("domain") or group.get("url") or "").replace("https://vk.com/", "").replace("vk.com/", "").strip("/")
        return {
            "domain": domain,
            "title": str(group.get("title") or domain),
            "lang": str(group.get("lang") or "ru"),
        }
    return {"domain": "", "title": "", "lang": "ru"}


def _extract_budget(text: str) -> str:
    patterns = [
        r"(?:бюджет|цена|оплата|гонорар)[:\s—-]*([^\n;,.]{2,80})",
        r"\bот\s+\d[\d\s]{2,}\s*(?:₽|руб\.?|р\.)",
        r"\bдо\s+\d[\d\s]{2,}\s*(?:₽|руб\.?|р\.)",
        r"\b\d[\d\s]{2,}\s*(?:₽|руб\.?|р\.)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()[:90]
    return ""


def _looks_like_order(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in ORDER_KEYWORDS)


def parse_vk_groups(groups: Iterable[Any], categories: Optional[List[str]] = None, *, token: Optional[str] = None, count: Optional[int] = None, only_orders: bool = True) -> List[Dict[str, str]]:
    """Parse VK public group walls and return normalized posts.

    Args:
        groups: list of strings or dicts: {domain,title,lang}
        categories: category keys from data.categories. Empty list means accept all categories.
        token: optional VK API token. If omitted, VK_TOKEN/.env is used.
        count: posts per group.
        only_orders: skip ordinary posts that do not look like freelance orders.
    """
    results: List[Dict[str, str]] = []
    categories = categories or []
    count = max(1, min(int(count or DEFAULT_COUNT), 100))

    for raw_group in groups:
        group = normalize_group(raw_group)
        domain = group["domain"]
        if not domain:
            continue
        title = group["title"]
        lang = group["lang"]

        try:
            payload = vk_api_call("wall.get", {"domain": domain, "count": count, "filter": "owner"}, token=token)
            posts = payload.get("response", {}).get("items", [])
            logger.info("VK group %s: %s posts", domain, len(posts))

            for post in posts:
                text = clean_html(post.get("text", ""))
                if not text:
                    continue
                if only_orders and not _looks_like_order(text):
                    continue
                if not matches_categories(text, categories, lang):
                    continue

                post_id = str(post.get("id", ""))
                owner_id = str(post.get("owner_id", ""))
                link = f"https://vk.com/wall{owner_id}_{post_id}" if owner_id and post_id else f"https://vk.com/{domain}"
                published = normalize_date(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(int(post.get("date") or 0))))
                budget = _extract_budget(text)

                results.append({
                    "unique_id": make_uid("vk", owner_id, post_id, text[:80]),
                    "source": f"VK: {title}",
                    "title": text[:100] + ("..." if len(text) > 100 else ""),
                    "description": text[:700],
                    "url": link,
                    "budget": budget,
                    "category": ", ".join(categories) if categories else "vk",
                    "published": published,
                })
            time.sleep(0.35)
        except Exception as exc:
            logger.warning("VK group error [%s]: %s", domain, exc)
    return results
