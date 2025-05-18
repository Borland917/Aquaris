import csv
import difflib
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes, ConversationHandler, MessageHandler,
    CallbackQueryHandler, filters
)

# Стан конверсейшена
CHOOSING = 0

# Завантажуємо таблицю сумісності
FISH_COMPAT = {}
with open('data/fish.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    header = next(reader)[1:]
    for row in reader:
        fish = row[0].lower()
        FISH_COMPAT[fish] = dict(zip(
            [h.lower() for h in header], row[1:]
        ))
# Список усіх видів для підказок
ALL_FISH = list(FISH_COMPAT.keys())

async def compat_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Показує діалог з кнопкою виходу і чекає на введення списку риб через кому.
    """
    keyboard = [[InlineKeyboardButton("Вийти ❌", callback_data="CANCEL")]]
    await update.message.reply_text(
        "🔗 Введіть назви риб через кому (Наприклад: Неон, Цихліда, Гуппі):",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CHOOSING

async def compat_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Обробляє введення користувачем. Виконує fuzzy matching для невідомих
    видів і перевіряє пари на несумісність.
    """
    text = update.message.text
    fishes = [s.strip().lower() for s in text.split(',') if s.strip()]

    known, unknown, suggestions = [], [], {}
    for fish in fishes:
        if fish in FISH_COMPAT:
            known.append(fish)
        else:
            # Пропозиція найближчих варіантів
            close = difflib.get_close_matches(fish, ALL_FISH, n=3, cutoff=0.6)
            if close:
                suggestions[fish] = close
            unknown.append(fish)

    if unknown:
        # Показуємо невідомі та пропозиції
        msg = "❌ Не знайдено: "
        for f in unknown:
            if f in suggestions:
                msg += f"— «{f}», можливо: {', '.join(suggestions[f])} "
            else:
                msg += f"— «{f}» "
        msg += "Спробуйте ще раз з правильною назвою."
        await update.message.reply_text(msg)
        return CHOOSING
        await update.message.reply_text(msg)
        return CHOOSING

    # Перевіряємо всі пари
    incompatible = []
    for i in range(len(known)):
        for j in range(i+1, len(known)):
            f1, f2 = known[i], known[j]
            status = FISH_COMPAT[f1].get(f2)
            if status == '❌':
                incompatible.append((f1.title(), f2.title()))

    # Формуємо відповідь
    if incompatible:
        msg = "⚠️ Знайдено несумісні пари:\n"
        msg += '\n'.join(f"— {a} та {b}" for a, b in incompatible)
    else:
        msg = "✅ Усі введені рибки сумісні між собою."

    await update.message.reply_text(msg)
    return ConversationHandler.END

async def compat_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Вихід з діалогу сумісності.
    """
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("❎ Вихід з Сумісності.")
    return ConversationHandler.END

from telegram.ext import CallbackQueryHandler as CQH, MessageHandler as MH


def get_compat_conversation_handler():
    return ConversationHandler(
        entry_points=[MH(filters.Regex(r"^🔗 Сумісність рибок$"), compat_menu)],
        states={CHOOSING: [MH(filters.TEXT & ~filters.COMMAND, compat_answer)]},
        fallbacks=[CQH(compat_cancel, pattern="^CANCEL$")]
    )