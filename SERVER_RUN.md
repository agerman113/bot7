# Запуск на сервере

## 1. Загрузка проекта

Распаковать архив на сервер:

```bash
unzip vk_parser_bot_client_ready.zip
cd freelance_parser_bot
```

## 2. Установка

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
```

Минимально заполнить:

```env
VK_TOKEN=реальный_токен
VK_GROUPS=domain_group_1,domain_group_2
PARSE_INTERVAL_MINUTES=10
VK_POSTS_PER_GROUP=30
```

## 3. Проверка

```bash
python audit_test.py
python live_test.py --category web_it --count 10 --groups 2
```

## 4. Запуск бота

```bash
python run.py
```

## 5. Локальная веб-панель

```bash
python web.py
```

Открыть:

```text
http://127.0.0.1:8080
```

## 6. systemd, если нужен постоянный запуск

Создать файл:

```bash
sudo nano /etc/systemd/system/vk-parser-bot.service
```

Пример:

```ini
[Unit]
Description=VK Parser Bot
After=network.target

[Service]
WorkingDirectory=/path/to/freelance_parser_bot
ExecStart=/path/to/freelance_parser_bot/.venv/bin/python run.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Запуск:

```bash
sudo systemctl daemon-reload
sudo systemctl enable vk-parser-bot
sudo systemctl start vk-parser-bot
sudo systemctl status vk-parser-bot
```
