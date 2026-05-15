"""Smoke checks for imports and route logic without real VK calls."""
from unittest.mock import patch

import bot


def main():
    assert bot.VK_GROUPS, "VK_GROUPS should not be empty"
    assert "web_it" in bot.CATEGORIES_RU, "web_it category missing"
    with patch("bot.send_message") as send:
        bot.handle_start(123)
        assert send.called, "handle_start did not send message"
    print("OK: smoke test passed")


if __name__ == "__main__":
    main()
