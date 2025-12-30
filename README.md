# Telegram-бот для расчёта аванса

Бот на **Python 3.12** и **aiogram v3** рассчитывает аванс и вторую часть зарплаты по производственному календарю РФ.

## Запуск

1. Создайте виртуальное окружение и установите зависимости:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Создайте файл `.env` и укажите токен бота:

```
BOT_TOKEN=ваш_токен
```

3. Запустите бота:

```bash
python -m bot.main
```

База SQLite создаётся автоматически в файле `bot.db`.
