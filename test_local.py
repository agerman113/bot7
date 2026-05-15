"""Offline tests for VK-only parser. No real internet/VK token required."""
from __future__ import annotations

import time
from unittest.mock import Mock, patch

from parsers.vk_parser import parse_vk_groups, set_vk_token


def fake_vk_response(*args, **kwargs):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "response": {
            "items": [
                {
                    "id": 101,
                    "owner_id": -1,
                    "date": int(time.time()),
                    "text": "Нужен программист: доработать VK бота, Python, API. Бюджет 1500 руб.",
                },
                {
                    "id": 102,
                    "owner_id": -1,
                    "date": int(time.time()),
                    "text": "Обычная новость группы без заказа",
                },
            ]
        }
    }
    return response


def main():
    set_vk_token("test-token")
    with patch("requests.get", side_effect=fake_vk_response) as mocked:
        items = parse_vk_groups([{"domain": "test_group", "title": "Test", "lang": "ru"}], ["web_it"], count=2)

    assert mocked.called, "VK API request was not made"
    assert len(items) == 1, f"Expected 1 order-like item, got {len(items)}"
    item = items[0]
    assert item["source"] == "VK: Test"
    assert "VK бота" in item["description"]
    assert "1500" in item["budget"]
    assert item["url"].startswith("https://vk.com/wall")
    print("OK: offline VK parser test passed")


if __name__ == "__main__":
    main()
