# ДДС Telegram-бот — инструкция запуска

## Установка

```bash
pip install -r requirements.txt
```

## Настройка

Создай файл `.env` или задай переменные окружения:

```bash
# Обязательно: токен Telegram-бота
# Получить у @BotFather в Telegram
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Опционально: ключ Claude API для умной категоризации
# Получить на console.anthropic.com
ANTHROPIC_API_KEY=sk-ant-...
```

## Запуск

```bash
# С переменными окружения напрямую:
TELEGRAM_BOT_TOKEN=ваш_токен python bot.py

# Или через .env файл (установи python-dotenv):
pip install python-dotenv
# Добавь в начало bot.py: from dotenv import load_dotenv; load_dotenv()
python bot.py
```

## Как пользоваться

1. Найди бота в Telegram и нажми /start
2. Нажми кнопку **📂 Загрузить выписку**
3. Выгрузи CSV из банка:
   - **Сбербанк**: СберБизнес → Выписки → Экспорт CSV
   - **Т-Банк**: Счета → Выписка → Скачать CSV  
   - **Модульбанк**: Операции → Экспорт → CSV
   - **ВТБ**: ВТБ Бизнес → Выписка → Excel
4. Отправь файл боту
5. Получи ДДС-отчёт в Excel

## Структура проекта

```
dds_bot/
├── bot.py          # Основной файл бота
├── parser.py       # Парсер CSV выписок (4 банка)
├── categorizer.py  # Категоризация через Claude AI
├── report.py       # Генерация Excel-отчёта
└── requirements.txt
```

## Деплой на Railway (бесплатно)

1. Создай аккаунт на railway.app
2. Создай новый проект → Deploy from GitHub
3. Добавь переменные окружения в Settings → Variables
4. Готово — бот работает 24/7
