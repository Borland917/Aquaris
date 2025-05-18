import logging
import datetime
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters, ConversationHandler
)
from apscheduler.schedulers.background import BackgroundScheduler

from config import BOT_TOKEN
from handlers.faq import get_faq_conversation_handler
from handlers.compatibility import get_compat_conversation_handler
from handlers.disease import get_disease_conversation_handler
from handlers.water_params import get_water_conversation_handler
from handlers.reminders import get_reminders_conversation_handler
from database.db import init_db, get_db, fetch_due_reminders

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Ініціалізуємо БД
init_db()

# Головне меню
main_menu = ReplyKeyboardMarkup(
    [
        ["❓ FAQ", "🔗 Сумісність рибок"],
        ["🩺 Хвороби рибок", "💧 Якість води"],
        ["⏰ Нагадування"]
    ],
    resize_keyboard=True
)

async def start(update: Update, context):
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=open('data/welcome.jpg', 'rb'),
        caption="👋 Ласкаво просимо до Aquaris Bot!"
    )
    await update.message.reply_text("Оберіть функцію:", reply_markup=main_menu)

async def menu_fallback(update: Update, context):
    logger.info(f"Fallback triggered for user {update.effective_user.id}: {update.message.text}")
    if context.user_data.get('conversation_state'):
        await update.message.reply_text(
            "Будь ласка, завершіть поточну дію або виберіть 'Вийти' у меню."
        )
        return
    await update.message.reply_text("Скористайтеся меню нижче:", reply_markup=main_menu)

async def cancel_conversation(update: Update, context):
    logger.info(f"Cancel conversation for user {update.effective_user.id}")
    context.user_data.clear()
    await update.message.reply_text(
        "❎ Розмову завершено. Оберіть функцію:", reply_markup=main_menu
    )
    return ConversationHandler.END

if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Команда /start
    app.add_handler(CommandHandler("start", start))

    # Команда /cancel
    app.add_handler(CommandHandler("cancel", cancel_conversation))

    # Меню-функції
    app.add_handler(get_faq_conversation_handler())
    app.add_handler(get_compat_conversation_handler())
    app.add_handler(get_disease_conversation_handler())
    app.add_handler(get_water_conversation_handler())
    app.add_handler(get_reminders_conversation_handler())

    # Загальний fallback
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, menu_fallback))

    # APScheduler для нагадувань
    scheduler = BackgroundScheduler(timezone="Europe/Kyiv")
    scheduler.add_job(
        lambda: [
            context.bot.send_message(chat_id=chat, text=f"⏰ {msg}")
            for chat, msg, _ in fetch_due_reminders(get_db(), datetime.datetime.now())
        ],
        trigger='interval', hours=1,
        next_run_time=datetime.datetime.now() + datetime.timedelta(seconds=10)
    )
    scheduler.start()
    logger.info("✅ Scheduler запущений")

    logger.info("✅ Бот запущено")
    app.run_polling()