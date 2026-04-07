import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from parsers import parse_csv
from report import generate_dds_report

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Хранилище транзакций (в памяти)
user_transactions = {}

WELCOME_TEXT = """
👋 Привет! Я помогу вести ДДС.

Что умею:
📂 Принять выписку CSV из банка
🏷 Автоматически категоризировать платежи
📊 Сформировать ДДС-отчёт в Excel

Поддерживаемые банки:
• Тинькофф / Т-Банк
• Сбербанк
• Модульбанк
• ВТБ

Просто отправь файл CSV — я всё обработаю!
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_TEXT)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📌 Команды:\n"
        "/start — начало работы\n"
        "/report — сформировать ДДС\n"
        "/clear — очистить данные\n"
        "/help — эта справка\n\n"
        "Просто отправь CSV-файл выписки из банка!"
    )

async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_transactions[uid] = []
    await update.message.reply_text("🗑 Данные очищены. Можно загружать новые файлы.")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    uid = update.effective_user.id

    if not doc.file_name.lower().endswith(".csv"):
        await update.message.reply_text("⚠️ Пожалуйста, отправь файл в формате CSV.")
        return

    await update.message.reply_text("⏳ Обрабатываю файл...")

    file = await context.bot.get_file(doc.file_id)
    file_bytes = await file.download_as_bytearray()
    csv_content = file_bytes.decode("utf-8-sig", errors="replace")

    result = parse_csv(csv_content, doc.file_name)

    if result["status"] == "error":
        await update.message.reply_text(
            "❌ Не удалось распознать формат банка.\n\n"
            "Поддерживаются: Тинькофф, Сбербанк, Модульбанк, ВТБ.\n"
            "Попробуй другой файл или напиши какой банк."
        )
        return

    if uid not in user_transactions:
        user_transactions[uid] = []
    user_transactions[uid].extend(result["transactions"])

    total = len(result["transactions"])
    income = sum(t["amount"] for t in result["transactions"] if t["amount"] > 0)
    expense = sum(t["amount"] for t in result["transactions"] if t["amount"] < 0)

    keyboard = [[InlineKeyboardButton("📊 Сформировать ДДС", callback_data="make_report")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ Файл загружен ({result['bank']})\n\n"
        f"📥 Транзакций: {total}\n"
        f"💚 Приходы: +{income:,.0f} ₽\n"
        f"🔴 Расходы: {expense:,.0f} ₽\n"
        f"💼 Итого: {income + expense:+,.0f} ₽\n\n"
        f"Всего в базе: {len(user_transactions[uid])} транзакций",
        reply_markup=reply_markup
    )

async def report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_report(update.effective_user.id, update.message, context)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "make_report":
        await send_report(query.from_user.id, query.message, context)

async def send_report(uid, message, context):
    transactions = user_transactions.get(uid, [])
    if not transactions:
        await message.reply_text("⚠️ Нет загруженных данных. Сначала отправь CSV-файл.")
        return

    await message.reply_text("📊 Формирую ДДС-отчёт...")
    filepath = generate_dds_report(transactions, uid)

    with open(filepath, "rb") as f:
        await message.reply_document(
            document=f,
            filename="ДДС_отчёт.xlsx",
            caption=(
                "✅ ДДС-отчёт готов!\n\n"
                "В файле:\n"
                "• Сводка по месяцам\n"
                "• Разбивка по категориям\n"
                "• Все транзакции"
            )
        )
    os.remove(filepath)

def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Укажи TELEGRAM_BOT_TOKEN в переменных окружения!")

    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("report", report_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()
