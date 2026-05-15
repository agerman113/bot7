"""Full offline audit for client handoff. Does not require VK_TOKEN or internet."""
from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import patch

os.environ.setdefault("VK_TOKEN", "test-token")
os.environ.setdefault("VK_GROUPS", "test_group,https://vk.com/test_group_2")

import bot  # noqa: E402
from data.categories import CATEGORIES_RU  # noqa: E402
from parsers.vk_parser import parse_vk_groups, set_vk_token  # noqa: E402
from test_local import fake_vk_response  # noqa: E402


def assert_keyboard_valid():
    keyboard = json.loads(bot.kb_categories(["web_it"], 0).get_keyboard())
    rows = keyboard.get("buttons", [])
    assert 1 <= len(rows) <= 10, f"VK keyboard row count invalid: {len(rows)}"
    assert any("Следующие" in row[0]["action"]["label"] for row in rows if row), "Next page button missing"


def assert_env_groups_loaded():
    domains = [group["domain"] for group in bot.VK_GROUPS]
    assert domains == ["test_group", "test_group_2"], domains


def assert_routes():
    bot.users.clear()
    with patch("bot.send_message") as send:
        bot.route_message(111, "/start")
        assert "VK-группах" in send.call_args.args[1]
    with patch("bot.send_message") as send:
        bot.route_message(111, "📋 Мои категории")
        assert send.call_args.args[1].startswith("📋 Категории"), send.call_args.args[1]
    with patch("bot.send_message") as send:
        bot.route_message(111, "📂 Категории")
        assert "Выбери категории" in send.call_args.args[1], send.call_args.args[1]
    with patch("bot.send_message") as send:
        bot.route_message(111, "➡️ Следующие")
        assert "Страница 2" in send.call_args.args[1], send.call_args.args[1]


def assert_parser_offline():
    set_vk_token("test-token")
    with patch("requests.get", side_effect=fake_vk_response):
        items = parse_vk_groups([{"domain": "test", "title": "Test", "lang": "ru"}], ["web_it"], count=2)
    assert len(items) == 1, items
    assert items[0]["url"].startswith("https://vk.com/wall")
    assert "1500" in items[0]["budget"]


def main():
    assert "web_it" in CATEGORIES_RU
    assert_env_groups_loaded()
    assert_keyboard_valid()
    assert_routes()
    assert_parser_offline()
    print("OK: full offline audit passed")


if __name__ == "__main__":
    main()
