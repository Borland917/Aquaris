import datetime
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, ConversationHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from database.db import get_db, add_reminder, fetch_reminders, delete_reminder

CHOOSING, TYPING_DAYS, TYPING_DATE, TYPING_DELETE = range(4)

async def remind_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Через дні 🗓", callback_data="SET_DAYS")],
        [InlineKeyboardButton("На дату 📆", callback_data="SET_DATE")],
        [InlineKeyboardButton("Видалити 🗑️", callback_data="SET_DELETE")],
        [InlineKeyboardButton("Вийти ❌", callback_data="CANCEL")]
    ]
    db = get_db()
    rems = fetch_reminders(db, update.effective_chat.id)
    text = "🔔 Ваші нагадування:\n"
    if rems:
        for rid, txt, dt, sent in rems:
            status = "✅" if sent else "🕓"
            text += f"{rid}. {txt} → {dt.date()} {status}\n"
    else:
        text += "— немає активних —\n"
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    return CHOOSING

async def set_days_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("📅 Введіть, через скільки днів (ціле число):")
    return TYPING_DAYS

async def received_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    days = update.message.text.strip()
    if not days.isdigit():
        return await update.message.reply_text("Введіть число.")
    remind_at = datetime.datetime.now() + datetime.timedelta(days=int(days))
    db = get_db()
    add_reminder(db, update.effective_chat.id, "Обслуговування акваріума", remind_at)
    await update.message.reply_text(f"✅ Нагадування на {remind_at.date()}")
    return ConversationHandler.END

async def set_date_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("📆 Введіть дату YYYY-MM-DD:")
    return TYPING_DATE

async def received_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        dt = datetime.datetime.strptime(update.message.text, "%Y-%m-%d")
    except ValueError:
        return await update.message.reply_text("Невірний формат. Спробуйте YYYY-MM-DD.")
    db = get_db()
    add_reminder(db, update.effective_chat.id, "Обслуговування акваріума", dt)
    await update.message.reply_text(f"✅ Нагадування на {dt.date()}")
    return ConversationHandler.END

async def set_delete_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("🗑️ Введіть ID нагадування для видалення:")
    return TYPING_DELETE

async def received_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text.isdigit():
        return await update.message.reply_text("ID має бути числом.")
    rid = int(text)
    db = get_db()
    if delete_reminder(db, rid):
        await update.message.reply_text(f"✅ Нагадування {rid} видалено.")
    else:
        await update.message.reply_text(f"❌ Нагадування з ID {rid} не знайдено.")
    return ConversationHandler.END

async def cancel_remind(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("❎ Вихід з Нагадувань.")
    return ConversationHandler.END

from telegram.ext import MessageHandler as MH, CallbackQueryHandler as CQH

def get_reminders_conversation_handler():
    return ConversationHandler(
        entry_points=[MH(filters.Regex("^⏰ Нагадування$"), remind_menu)],
        states={
            CHOOSING: [
                CQH(set_days_cb,   pattern="^SET_DAYS$"),
                CQH(set_date_cb,   pattern="^SET_DATE$"),
                CQH(set_delete_cb, pattern="^SET_DELETE$"),
                CQH(cancel_remind, pattern="^CANCEL$"),
            ],
            TYPING_DAYS:  [MH(filters.TEXT & ~filters.COMMAND, received_days)],
            TYPING_DATE:  [MH(filters.TEXT & ~filters.COMMAND, received_date)],
            TYPING_DELETE:[MH(filters.TEXT & ~filters.COMMAND, received_delete)],
        },
        fallbacks=[CQH(cancel_remind, pattern="^CANCEL$")]
    )