"""Local VK parser dashboard.
Run: python web.py -> http://127.0.0.1:8080
"""
from __future__ import annotations

import html
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from data.categories import CATEGORIES_RU
from data.sources import load_vk_groups_from_env
from parsers.vk_parser import parse_vk_groups, set_vk_token

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


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


load_dotenv_file()
os.environ.setdefault("HTTP_TIMEOUT_SECONDS", "8")
VK_GROUPS = load_vk_groups_from_env()
set_vk_token(os.environ.get("VK_PARSER_TOKEN") or os.environ.get("VK_SERVICE_TOKEN") or os.environ.get("VK_TOKEN", ""))


def render_page(items=None, error="", category="web_it"):
    items = items or []
    options = "".join(
        f'<option value="{html.escape(key)}" {"selected" if key == category else ""}>{html.escape(label)}</option>'
        for key, label in CATEGORIES_RU.items()
    )
    cards = "".join(
        f"""
        <article class="card">
          <div class="meta">{html.escape(item.get('source', 'VK'))} · {html.escape(item.get('published', ''))}</div>
          <h3>{html.escape(item.get('title', ''))}</h3>
          <p>{html.escape(item.get('description', ''))}</p>
          <div class="budget">{html.escape(item.get('budget', ''))}</div>
          <a href="{html.escape(item.get('url', '#'))}" target="_blank">Открыть пост VK</a>
        </article>
        """
        for item in items
    )
    groups = ", ".join(group["domain"] for group in VK_GROUPS)
    return f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>VK Parser Bot</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 0; background:#f6f7fb; color:#111827; }}
.wrap {{ max-width: 980px; margin: 0 auto; padding: 28px; }}
.panel {{ background:white; padding:22px; border-radius:18px; box-shadow:0 10px 30px rgba(15,23,42,.08); }}
.row {{ display:flex; gap:12px; flex-wrap:wrap; align-items:center; }}
select,input,button {{ padding:12px 14px; border:1px solid #d1d5db; border-radius:12px; font-size:15px; }}
button {{ background:#2563eb; color:white; cursor:pointer; border:none; font-weight:700; }}
.card {{ background:white; margin:16px 0; padding:18px; border-radius:16px; box-shadow:0 6px 20px rgba(15,23,42,.06); }}
.meta {{ color:#6b7280; font-size:13px; }}
h1 {{ margin-top:0; }}
a {{ color:#2563eb; font-weight:700; }}
.error {{ color:#b91c1c; background:#fee2e2; padding:12px; border-radius:12px; }}
.budget {{ color:#047857; font-weight:700; margin:8px 0; }}
.small {{ color:#6b7280; font-size:13px; }}
</style>
</head>
<body><main class="wrap">
<section class="panel">
<h1>VK Parser Bot</h1>
<p>Проверка заказов только из VK-групп. Подключено групп: <b>{len(VK_GROUPS)}</b></p>
<p class="small">Группы: {html.escape(groups)}</p>
<form method="get" action="/fetch" class="row">
<select name="category">{options}</select>
<input name="count" type="number" min="1" max="100" value="30" title="Постов на группу">
<button type="submit">Проверить VK</button>
</form>
{f'<p class="error">{html.escape(error)}</p>' if error else ''}
</section>
{cards if cards else '<p class="small">Результаты появятся после проверки.</p>'}
</main></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type="text/html; charset=utf-8"):
        raw = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format, *args):
        return

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path in {"/", "/index.html"}:
            self._send(200, render_page())
            return
        if parsed.path == "/health":
            self._send(200, json.dumps({"ok": True, "mode": "vk-only", "groups": len(VK_GROUPS)}, ensure_ascii=False), "application/json; charset=utf-8")
            return
        if parsed.path == "/fetch":
            qs = parse_qs(parsed.query)
            category = qs.get("category", ["web_it"])[0]
            try:
                count = int(qs.get("count", ["30"])[0])
            except ValueError:
                count = 30
            try:
                items = parse_vk_groups(VK_GROUPS, [category] if category else [], count=count, only_orders=True)
                self._send(200, render_page(items=items, category=category))
            except Exception as exc:
                self._send(200, render_page(error=str(exc), category=category))
            return
        self._send(404, "Not found", "text/plain; charset=utf-8")


def main():
    port = int(os.environ.get("PORT", "8080"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"VK parser dashboard: http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
