"""Live VK parser check. Requires real VK_TOKEN in .env/environment."""
from __future__ import annotations

import argparse
import os

from data.sources import load_vk_groups_from_env
from parsers.vk_parser import parse_vk_groups, set_vk_token


def load_dotenv_file(path=".env"):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", default="web_it")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--groups", type=int, default=2)
    args = parser.parse_args()

    load_dotenv_file()
    token = os.environ.get("VK_PARSER_TOKEN") or os.environ.get("VK_SERVICE_TOKEN") or os.environ.get("VK_TOKEN", "")
    if not token or token.startswith("YOUR_"):
        raise SystemExit("VK_TOKEN is required for live_test.py")
    set_vk_token(token)
    vk_groups = load_vk_groups_from_env()

    groups = vk_groups[: max(1, args.groups)]
    items = parse_vk_groups(groups, [args.category], count=args.count, only_orders=True)
    print(f"Found: {len(items)}")
    for item in items[:10]:
        print("-", item["title"], item["url"])


if __name__ == "__main__":
    main()
