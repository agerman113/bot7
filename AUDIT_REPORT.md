# Аудит и проверка VK Parser Bot

## Статус
Проект подготовлен под исходное задание: бот-парсер **только для VK-групп**. Лишние источники Kwork/FL/RSS/Telegram не используются.

## Что исправлено

1. `VK_GROUPS` из `.env` теперь реально применяется после загрузки `.env`.
2. Исправлен роутинг кнопки `📋 Мои категории`: раньше она могла открывать выбор категорий из-за совпадения слова «категории».
3. Исправлена клавиатура категорий: добавлена пагинация, чтобы не превышать ограничения VK по строкам клавиатуры.
4. Бот не требует `config.json`, если задан `.env`.
5. Парсер изолирован под VK API `wall.get`.
6. Добавлены offline-аудит тесты без реального VK-токена.
7. Проверена локальная веб-панель `/` и `/health`.

## Проверки, которые пройдены

```bash
python -m py_compile bot.py web.py parsers/vk_parser.py test_local.py smoke_test.py live_test.py audit_test.py
python test_local.py
python smoke_test.py
python audit_test.py
```

Веб-панель проверена локально:

```text
GET /health -> {"ok": true, "mode": "vk-only", "groups": 5}
GET / -> страница открывается
```

## Что невозможно проверить без клиента

Live-парсинг VK и отправку сообщений в VK нельзя честно подтвердить без действующего `VK_TOKEN`. Offline-тесты подменяют ответ VK API и проверяют логику парсинга, фильтрации, бюджета, ссылок и роутинга.

## Как проверить на сервере клиента

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
python audit_test.py
python live_test.py --category web_it --count 10 --groups 2
python run.py
```

Для Windows:

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python audit_test.py
python live_test.py --category web_it --count 10 --groups 2
python run.py
```
