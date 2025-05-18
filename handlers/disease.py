# handlers/disease.py

import logging
import aiohttp
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from database.diseases import DISEASE_LABELS, TREATMENTS
from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_ENDPOINT

logger = logging.getLogger(__name__)

# Власна асинхронна функція для запиту до OpenRouter
async def fetch_from_llm(prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": "Ти асистент з діагностики рибячих хвороб. Відповідай українською."},
            {"role": "user",   "content": prompt},
        ],
        "max_tokens": 200,
        "temperature": 0.2,
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(OPENROUTER_ENDPOINT, json=payload, headers=headers) as resp:
            data = await resp.json()
            # Перевірка структури відповіді
            return data["choices"][0]["message"]["content"].strip()

ASK_SYMPTOMS = 0

async def disease_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Вийти ❌", callback_data="CANCEL")]]
    await update.message.reply_text(
        "🩺 Опишіть симптоми рибки, наприклад:\n"
        "Моя рибка втратила апетит і у неї білі плями на плавниках.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ASK_SYMPTOMS

async def disease_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    symptoms = update.message.text.strip()
    # Оголошуємо prompt тут
    prompt = (
        f"На основі цих симптомів рибки класифікуй захворювання "
        f"по одній з міток:\n{', '.join(DISEASE_LABELS)}\n"
        f"Симптоми: {symptoms}\n"
        "Відповідай тільки назвою хвороби."
    )
    await update.message.reply_text("🔄 Аналізую через ШІ…")
    try:
        raw = await fetch_from_llm(prompt)
    except Exception as e:
        logger.error(f"fetch_from_llm error: {e}")
        await update.message.reply_text(f"❌ Помилка ШІ: {e}")
        return ConversationHandler.END

    # Очищення відповіді від markdown
    cleaned = raw.replace("```", "").replace("`", "").replace("*", "").strip()
    disease_name = cleaned.splitlines()[0]
    key = disease_name.lower()

    # Статичний словник порад
    treatment = TREATMENTS.get(
        key,
        "Рекомендації відсутні для цього діагнозу."
    )
    await update.message.reply_text(
        f"Діагноз: {disease_name}\n"
        f"Рекомендації: {treatment}"
    )
    return ConversationHandler.END

async def disease_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("❎ Вихід з діагностики хвороб.")
    return ConversationHandler.END

from telegram.ext import CallbackQueryHandler as CQH, MessageHandler as MH

def get_disease_conversation_handler():
    return ConversationHandler(
        entry_points=[MH(filters.Regex(r"^🩺 Хвороби рибок$"), disease_menu)],
        states={ASK_SYMPTOMS: [MH(filters.TEXT & ~filters.COMMAND, disease_answer)]},
        fallbacks=[CQH(disease_cancel, pattern="^CANCEL$")],
    )