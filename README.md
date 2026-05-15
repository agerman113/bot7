# VK Parser Bot

Готовая версия под задачу: **только VK**, без Kwork/FL/RSS/Telegram/Upwork.

## Что делает

- читает стены публичных VK-групп через VK API `wall.get`;
- ищет посты, похожие на заказы: «нужен», «требуется», «доработать», «бот», «парсер», «сайт», «API», «бюджет» и т.д.;
- фильтрует по категориям;
- отправляет новые найденные посты в VK-бота;
- хранит уже отправленные посты в `data/seen_ids.json`, чтобы не спамить дублями;
- имеет локальную панель проверки `http://127.0.0.1:8080`.

## Быстрый запуск

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

В `.env` обязательно вставить реальный токен:

```env
VK_TOKEN=...
VK_GROUPS=freelance_ru,freelance,remote_work,webdev_for_you,python_jobs
PARSE_INTERVAL_MINUTES=10
VK_POSTS_PER_GROUP=30
```

Запуск бота:

```bash
python run.py
```

Локальная проверка веб-панели:

```bash
python web.py
```

Открыть:

```text
http://127.0.0.1:8080
```

## Проверки

Без интернета и без токена:

```bash
python -m py_compile bot.py web.py parsers/vk_parser.py test_local.py smoke_test.py
python test_local.py
python smoke_test.py
```

С реальным токеном VK:

```bash
python live_test.py --category web_it --count 10 --groups 2
```

## Где менять VK-группы

В `.env`:

```env
VK_GROUPS=freelance_ru,remote_work,python_jobs
```

Или в `data/sources.py`.

## Важно

Для реального запуска нужен действующий `VK_TOKEN`. Без токена локальные offline-тесты проходят, но live-парсинг VK невозможен, потому что VK API требует access token.

## Перед передачей клиенту

В этой версии добавлены:

- `audit_test.py` — полный offline-аудит без VK-токена;
- `AUDIT_REPORT.md` — отчёт по проверке;
- `SERVER_RUN.md` — инструкция для сервера;
- пагинация категорий в VK-клавиатуре;
- корректная загрузка `VK_GROUPS` из `.env`.

Рекомендуемая проверка перед запуском:

```bash
python -m py_compile bot.py web.py parsers/vk_parser.py test_local.py smoke_test.py live_test.py audit_test.py
python audit_test.py
```
