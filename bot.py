"""VK Parser Bot.

VK-only bot for finding order-like posts in configured VK groups.
Configuration priority: environment/.env -> config.json -> defaults.
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Dict, List

import vk_api
from vk_api.keyboard import VkKeyboard, VkKeyboardColor
from vk_api.longpoll import VkEventType, VkLongPoll

from data.categories import CATEGORIES_RU
from data.sources import load_vk_groups_from_env
from parsers.vk_parser import parse_vk_groups, set_vk_token

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(LOG_DIR, exist_ok=True)
os.makedirs(DATA_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "bot.log"), encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def load_dotenv_file(path: str = ".env") -> None:
    env_path = path if os.path.isabs(path) else os.path.join(BASE_DIR, path)
    if not os.path.exists(env_path):
        return
    with open(env_path, encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def load_config() -> Dict[str, object]:
    load_dotenv_file()
    config_path = os.path.join(BASE_DIR, "config.json")
    data: Dict[str, object] = {}
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as file:
                data = json.load(file)
        except Exception as exc:
            logger.warning("config.json не прочитан: %s", exc)

    parser_token = (
        os.environ.get("VK_PARSER_TOKEN")
        or os.environ.get("VK_SERVICE_TOKEN")
        or os.environ.get("VK_TOKEN")
        or str(data.get("vk_parser_token") or data.get("vk_service_token") or data.get("vk_token") or "")
    )
    bot_token = (
        os.environ.get("VK_BOT_TOKEN")
        or os.environ.get("VK_TOKEN")
        or str(data.get("vk_bot_token") or data.get("vk_token") or "")
    )
    admin_ids_raw = os.environ.get("ADMIN_IDS")
    if admin_ids_raw is None:
        admin_ids_raw = ",".join(map(str, data.get("admin_ids") or []))
    interval_raw = os.environ.get("PARSE_INTERVAL_MINUTES") or str(data.get("parse_interval_minutes") or "10")
    posts_raw = os.environ.get("VK_POSTS_PER_GROUP") or str(data.get("vk_posts_per_group") or "30")

    try:
        interval = max(1, int(interval_raw))
    except ValueError:
        interval = 10
    try:
        posts_per_group = max(1, min(int(posts_raw), 100))
    except ValueError:
        posts_per_group = 30

    admin_ids: List[int] = []
    for part in str(admin_ids_raw or "").split(","):
        part = part.strip()
        if part.isdigit():
            admin_ids.append(int(part))

    return {
        "vk_token": parser_token.strip(),
        "vk_bot_token": bot_token.strip(),
        "admin_ids": admin_ids,
        "parse_interval_minutes": interval,
        "vk_posts_per_group": posts_per_group,
    }


CONFIG = load_config()
VK_TOKEN = str(CONFIG["vk_token"])
VK_BOT_TOKEN = str(CONFIG["vk_bot_token"])
ADMIN_IDS = CONFIG["admin_ids"]
PARSE_INTERVAL = int(CONFIG["parse_interval_minutes"])
VK_POSTS_PER_GROUP = int(CONFIG["vk_posts_per_group"])
set_vk_token(VK_TOKEN)
VK_GROUPS = load_vk_groups_from_env()

USERS_FILE = os.path.join(DATA_DIR, "users.json")
SEEN_FILE = os.path.join(DATA_DIR, "seen_ids.json")


def load_json(path: str, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return default


def save_json(path: str, data) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


users: Dict[str, Dict[str, object]] = load_json(USERS_FILE, {})
seen_ids = set(load_json(SEEN_FILE, []))

vk_session = None
vk = None
longpoll = None


def setup_vk():
    global vk_session, vk, longpoll
    if not VK_BOT_TOKEN or VK_BOT_TOKEN.startswith("YOUR_"):
        raise RuntimeError("Не задан VK_BOT_TOKEN. Заполни .env перед запуском бота.")
    if vk_session is None:
        vk_session = vk_api.VkApi(token=VK_BOT_TOKEN)
        vk = vk_session.get_api()
        longpoll = VkLongPoll(vk_session)
    return vk, longpoll


def save_users() -> None:
    save_json(USERS_FILE, users)


def save_seen() -> None:
    save_json(SEEN_FILE, sorted(seen_ids))


def get_user(user_id: int) -> Dict[str, object]:
    uid = str(user_id)
    if uid not in users:
        users[uid] = {"categories": ["web_it"], "active": True, "menu": "main"}
        save_users()
    return users[uid]


def kb_main_menu():
    kb = VkKeyboard(one_time=False)
    kb.add_button("📂 Категории", color=VkKeyboardColor.PRIMARY)
    kb.add_button("📋 Мои категории", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("🔄 Проверить VK сейчас", color=VkKeyboardColor.POSITIVE)
    kb.add_button("🔔 Подписка вкл/выкл", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("ℹ️ Помощь", color=VkKeyboardColor.SECONDARY)
    return kb


CATEGORY_PAGE_SIZE = 12


def get_category_page(user: Dict[str, object]) -> int:
    try:
        return max(0, int(user.get("category_page", 0)))
    except Exception:
        return 0


def kb_categories(selected: List[str], page: int = 0):
    """VK keyboards have row/count limits, so categories are paginated."""
    kb = VkKeyboard(one_time=False)
    items = list(CATEGORIES_RU.items())
    total_pages = max(1, (len(items) + CATEGORY_PAGE_SIZE - 1) // CATEGORY_PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    chunk = items[page * CATEGORY_PAGE_SIZE:(page + 1) * CATEGORY_PAGE_SIZE]

    for index, (key, label) in enumerate(chunk):
        mark = "✅ " if key in selected else ""
        color = VkKeyboardColor.POSITIVE if key in selected else VkKeyboardColor.SECONDARY
        kb.add_button(f"{mark}{label}", color=color)
        if (index + 1) % 2 == 0 and index + 1 < len(chunk):
            kb.add_line()

    kb.add_line()
    if page > 0:
        kb.add_button("⬅️ Предыдущие", color=VkKeyboardColor.SECONDARY)
    if page < total_pages - 1:
        kb.add_button("➡️ Следующие", color=VkKeyboardColor.SECONDARY)
    kb.add_line()
    kb.add_button("✅ Выбрать все", color=VkKeyboardColor.PRIMARY)
    kb.add_button("❌ Снять все", color=VkKeyboardColor.NEGATIVE)
    kb.add_line()
    kb.add_button("◀️ Назад", color=VkKeyboardColor.SECONDARY)
    return kb


def send_message(user_id: int, text: str, keyboard=None) -> None:
    try:
        api, _ = setup_vk()
        params = {
            "user_id": user_id,
            "message": text[:3900],
            "random_id": int(time.time() * 1_000_000),
        }
        if keyboard:
            params["keyboard"] = keyboard.get_keyboard()
        api.messages.send(**params)
    except Exception as exc:
        logger.error("send_message error to %s: %s", user_id, exc)


def format_item(item: Dict[str, str]) -> str:
    lines = []
    if item.get("source"):
        lines.append(f"📌 {item['source']}")
    if item.get("title"):
        lines.append(f"📝 {item['title']}")
    if item.get("description"):
        desc = item["description"][:500] + ("..." if len(item["description"]) > 500 else "")
        lines.append(f"💬 {desc}")
    if item.get("budget"):
        lines.append(f"💰 {item['budget']}")
    if item.get("url"):
        lines.append(f"🔗 {item['url']}")
    if item.get("published"):
        lines.append(f"🕐 {item['published']}")
    return "\n".join(lines)


def run_vk_parser(categories: List[str], dedupe: bool = True) -> List[Dict[str, str]]:
    items = parse_vk_groups(VK_GROUPS, categories, token=VK_TOKEN, count=VK_POSTS_PER_GROUP, only_orders=True)
    fresh = []
    for item in items:
        uid = item.get("unique_id") or item.get("url") or item.get("title")
        if not uid:
            continue
        if not dedupe or uid not in seen_ids:
            seen_ids.add(uid)
            fresh.append(item)
    if fresh and dedupe:
        save_seen()
    return fresh


def handle_start(user_id: int) -> None:
    user = get_user(user_id)
    user["menu"] = "main"
    save_users()
    send_message(
        user_id,
        "👋 Бот готов искать заказы только во VK-группах.\n\n"
        "По умолчанию включена категория IT/разработка. Можно выбрать другие категории и нажать «Проверить VK сейчас».\n"
        f"Групп подключено: {len(VK_GROUPS)}. Автопроверка: каждые {PARSE_INTERVAL} мин.",
        kb_main_menu(),
    )


def handle_categories(user_id: int) -> None:
    user = get_user(user_id)
    user["menu"] = "categories"
    save_users()
    page = get_category_page(user)
    send_message(user_id, f"Выбери категории для VK-парсинга. Страница {page + 1}.", kb_categories(user.get("categories", []), page))


def handle_toggle_category(user_id: int, text: str) -> None:
    user = get_user(user_id)
    selected = list(user.get("categories", []))
    clean = text.replace("✅ ", "").strip()
    matched = None
    for key, label in CATEGORIES_RU.items():
        if label == clean:
            matched = key
            break
    if not matched:
        send_message(user_id, "Категория не распознана.", kb_categories(selected, get_category_page(user)))
        return
    if matched in selected:
        selected.remove(matched)
    else:
        selected.append(matched)
    user["categories"] = selected
    save_users()
    labels = [CATEGORIES_RU.get(key, key) for key in selected]
    send_message(user_id, "✅ Выбрано: " + (", ".join(labels) if labels else "ничего"), kb_categories(selected, get_category_page(user)))


def handle_my_categories(user_id: int) -> None:
    user = get_user(user_id)
    labels = [CATEGORIES_RU.get(key, key) for key in user.get("categories", [])]
    send_message(user_id, "📋 Категории:\n• " + "\n• ".join(labels) if labels else "📋 Категории не выбраны.", kb_main_menu())


def handle_select_all(user_id: int) -> None:
    user = get_user(user_id)
    user["categories"] = list(CATEGORIES_RU.keys())
    save_users()
    send_message(user_id, "✅ Все категории выбраны.", kb_categories(user["categories"], get_category_page(user)))


def handle_clear_all(user_id: int) -> None:
    user = get_user(user_id)
    user["categories"] = []
    save_users()
    send_message(user_id, "❌ Категории сняты. Без категорий бот принимает все подходящие VK-посты.", kb_categories([], get_category_page(user)))


def handle_toggle_subscription(user_id: int) -> None:
    user = get_user(user_id)
    user["active"] = not bool(user.get("active", True))
    save_users()
    send_message(user_id, "🔔 Автоуведомления включены." if user["active"] else "🔕 Автоуведомления отключены.", kb_main_menu())


def handle_fetch_now(user_id: int) -> None:
    user = get_user(user_id)
    categories = list(user.get("categories", []))
    send_message(user_id, "🔄 Проверяю VK-группы...")

    def worker():
        items = run_vk_parser(categories, dedupe=True)
        if not items:
            send_message(user_id, "Пока новых VK-заказов нет.", kb_main_menu())
            return
        send_message(user_id, f"🎯 Найдено новых VK-заказов: {len(items)}")
        for item in items[:15]:
            send_message(user_id, format_item(item))
            time.sleep(0.35)
        send_message(user_id, "Готово.", kb_main_menu())

    threading.Thread(target=worker, daemon=True).start()


def handle_help(user_id: int) -> None:
    groups = ", ".join(group["domain"] for group in VK_GROUPS[:10])
    send_message(
        user_id,
        "ℹ️ Бот парсит только VK.\n\n"
        "Команды:\n"
        "• 📂 Категории — фильтр по тематике\n"
        "• 🔄 Проверить VK сейчас — ручной поиск\n"
        "• 🔔 Подписка — автоматическая отправка новых постов\n\n"
        f"VK-группы: {groups}\n"
        "Чтобы заменить группы, отредактируй VK_GROUPS в .env через запятую.",
        kb_main_menu(),
    )


def route_message(user_id: int, text: str) -> None:
    user = get_user(user_id)
    menu = str(user.get("menu", "main"))
    lowered = (text or "").lower().strip()

    if lowered in {"/start", "start", "начать", "старт"}:
        handle_start(user_id)
    elif "мои категории" in lowered or "📋" in text:
        handle_my_categories(user_id)
    elif "категор" in lowered or "📂" in text:
        handle_categories(user_id)
    elif "проверить" in lowered or "обновить" in lowered or "🔄" in text:
        handle_fetch_now(user_id)
    elif "подписка" in lowered or "🔔" in text:
        handle_toggle_subscription(user_id)
    elif "помощь" in lowered or "help" in lowered or "ℹ️" in text:
        handle_help(user_id)
    elif "выбрать все" in lowered:
        handle_select_all(user_id)
    elif "снять все" in lowered or "❌" in text:
        handle_clear_all(user_id)
    elif "следующие" in lowered or "➡️" in text:
        user["category_page"] = get_category_page(user) + 1
        save_users()
        handle_categories(user_id)
    elif "предыдущие" in lowered or "⬅️" in text:
        user["category_page"] = max(0, get_category_page(user) - 1)
        save_users()
        handle_categories(user_id)
    elif "назад" in lowered or "◀️" in text:
        user["menu"] = "main"
        save_users()
        send_message(user_id, "Главное меню:", kb_main_menu())
    elif menu == "categories":
        handle_toggle_category(user_id, text)
    else:
        send_message(user_id, "Используй кнопки меню.", kb_main_menu())


def background_parser() -> None:
    logger.info("VK background parser started")
    while True:
        time.sleep(PARSE_INTERVAL * 60)
        for uid, data in list(users.items()):
            if not data.get("active", True):
                continue
            try:
                items = run_vk_parser(list(data.get("categories", [])), dedupe=True)
                if items:
                    send_message(int(uid), f"🔔 Новые VK-заказы: {len(items)}")
                    for item in items[:20]:
                        send_message(int(uid), format_item(item))
                        time.sleep(0.35)
            except Exception as exc:
                logger.exception("Background error for %s: %s", uid, exc)


def main() -> None:
    setup_vk()
    threading.Thread(target=background_parser, daemon=True).start()
    logger.info("VK bot started. Groups: %s", [group["domain"] for group in VK_GROUPS])
    _, lp = setup_vk()
    for event in lp.listen():
        if event.type == VkEventType.MESSAGE_NEW and event.to_me:
            try:
                route_message(event.user_id, (event.text or "").strip())
            except Exception as exc:
                logger.exception("Handler error: %s", exc)


if __name__ == "__main__":
    main()
