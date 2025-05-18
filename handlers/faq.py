import json
import aiohttp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, MessageHandler,
    CallbackQueryHandler, filters
)
from config import OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_ENDPOINT

ASK_QUESTION = 0

with open('data/faq.json', 'r', encoding='utf-8') as f:
    FAQ_DATA = json.load(f)

async def faq_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("Вийти ❌", callback_data="CANCEL")]]
    await update.message.reply_text(
        "📘 Введіть питання про догляд за акваріумом або натисніть Вийти:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ASK_QUESTION

async def faq_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.lower()
    for q,a in FAQ_DATA.items():
        if q in query:
            await update.message.reply_text(f"📘 {a}")
            return ConversationHandler.END
    # фолбек до ШІ
    await update.message.reply_text("🔄 Шукаю відповідь у ШІ...")
    headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}"}
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role":"system","content":"Ти асистент з акваріумного догляду. Відповідай українською."},
            {"role":"user","content": update.message.text}
        ],
        "max_tokens":200
    }
    async with aiohttp.ClientSession() as session:
        resp = await session.post(OPENROUTER_ENDPOINT, json=payload, headers=headers)
        data = await resp.json()
        choices = data.get('choices', [])
        ans = choices[0]['message']['content'] if choices else "Вибачте, не зміг знайти відповідь."
    await update.message.reply_text(f"🤖 {ans}")
    return ConversationHandler.END

async def faq_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("❎ Вихід з FAQ.")
    return ConversationHandler.END

from telegram.ext import CallbackQueryHandler as CQH, MessageHandler as MH

def get_faq_conversation_handler():
    return ConversationHandler(
        entry_points=[MH(filters.Regex("^❓ FAQ$"), faq_menu)],
        states={ ASK_QUESTION: [MH(filters.TEXT & ~filters.COMMAND, faq_answer)] },
        fallbacks=[CQH(faq_cancel, pattern="^CANCEL$")]
    )