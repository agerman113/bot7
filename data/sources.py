"""VK sources. Add/remove public VK groups here or through VK_GROUPS env."""
from __future__ import annotations

import os
from typing import Any, Dict, List

DEFAULT_VK_GROUPS: List[Dict[str, str]] = [
    {"domain": "freelance_ru", "title": "Фриланс RU", "lang": "ru"},
    {"domain": "freelance", "title": "Фриланс", "lang": "ru"},
    {"domain": "remote_work", "title": "Удалённая работа", "lang": "ru"},
    {"domain": "webdev_for_you", "title": "Web-разработка", "lang": "ru"},
    {"domain": "python_jobs", "title": "Python Jobs", "lang": "ru"},
]


def normalize_vk_group(item: Any) -> Dict[str, str]:
    if isinstance(item, dict):
        raw = str(item.get("domain") or item.get("url") or "")
        title = str(item.get("title") or raw)
        lang = str(item.get("lang") or "ru")
    else:
        raw = str(item or "")
        title = raw
        lang = "ru"
    domain = raw.strip().replace("https://vk.com/", "").replace("http://vk.com/", "").replace("vk.com/", "").strip("/")
    return {"domain": domain, "title": title.strip() or domain, "lang": lang}


def load_vk_groups_from_env() -> List[Dict[str, str]]:
    raw = os.environ.get("VK_GROUPS", "").strip()
    if not raw:
        return list(DEFAULT_VK_GROUPS)
    groups: List[Dict[str, str]] = []
    for item in raw.split(","):
        group = normalize_vk_group(item)
        if group["domain"]:
            groups.append(group)
    return groups or list(DEFAULT_VK_GROUPS)


# Backward-compatible default. Main modules refresh this after loading .env.
VK_GROUPS = load_vk_groups_from_env()
