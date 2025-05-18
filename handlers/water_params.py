import datetime
import json
import os
import logging
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton, InputFile
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MENU_CHOICE, ASK_PH, ASK_TEMP, ASK_AMMONIA = range(4)

DATA_PATH = "data/water_params.json"

async def water_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("➕ Додати параметри", callback_data="ADD_PARAMS")],
        [InlineKeyboardButton("📊 Переглянути графік", callback_data="SHOW_GRAPH")],
        [InlineKeyboardButton("Вийти ❌", callback_data="CANCEL")]
    ]
    await update.message.reply_text(
        "💧 Якість води:\nЩо бажаєте зробити?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MENU_CHOICE

async def restart_water_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("➕ Додати параметри", callback_data="ADD_PARAMS")],
        [InlineKeyboardButton("📊 Переглянути графік", callback_data="SHOW_GRAPH")],
        [InlineKeyboardButton("Вийти ❌", callback_data="CANCEL")]
    ]
    await update.message.reply_text(
        "💧 Якість води:\nЩо бажаєте зробити?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MENU_CHOICE

async def handle_water_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "ADD_PARAMS":
        await query.edit_message_text("💧 Введіть значення pH (наприклад: 7.5):")
        return ASK_PH
    elif query.data == "SHOW_GRAPH":
        await query.edit_message_text("📊 Створюю графіки параметрів...")
        await send_graph(update, context)
        return ConversationHandler.END
    elif query.data == "CANCEL":
        await query.edit_message_text("❎ Вихід з розділу якості води.")
        return ConversationHandler.END

async def invalid_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Невірне введення. Скористайтеся меню або введіть коректні дані.")
    return None

async def received_ph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        ph = float(text)
        if not (0 <= ph <= 14):
            await update.message.reply_text("pH має бути від 0 до 14. Спробуйте ще раз (наприклад, 7.5):")
            return ASK_PH
    except ValueError:
        await update.message.reply_text("Невірне pH. Введіть число, наприклад, 7.5:")
        return ASK_PH
    context.user_data['ph'] = ph
    await update.message.reply_text("🌡️ Введіть температуру у °C (наприклад: 25):")
    return ASK_TEMP

async def received_temp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace('°', '')
    try:
        temp = float(text)
        if not (10 <= temp <= 40):
            await update.message.reply_text("Температура має бути від 10 до 40°C. Спробуйте ще раз (наприклад, 25):")
            return ASK_TEMP
    except ValueError:
        await update.message.reply_text("Невірна температура. Введіть число, наприклад, 25:")
        return ASK_TEMP
    context.user_data['temp'] = temp
    await update.message.reply_text("🧪 Введіть рівень аміаку в ppm (наприклад: 0.5):")
    return ASK_AMMONIA

async def received_ammonia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip().replace('ppm', '')
    try:
        ammonia = float(text)
        if not (0 <= ammonia <= 10):
            await update.message.reply_text("Аміак має бути від 0 до 10 ppm. Спробуйте ще раз (наприклад, 0.5):")
            return ASK_AMMONIA
    except ValueError:
        await update.message.reply_text("Невірний аміак. Введіть число, наприклад, 0.5:")
        return ASK_AMMONIA

    ph = context.user_data['ph']
    temp = context.user_data['temp']
    user_id = str(update.message.from_user.id)
    record = {
        "timestamp": datetime.datetime.now().isoformat(),
        "ph": ph,
        "temp": temp,
        "ammonia": ammonia
    }
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = {}

    if user_id not in data:
        data[user_id] = []
    data[user_id].append(record)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    issues = []
    if ph < 6.5:
        issues.append("pH занизький — підвищте карбонатну жорсткість.")
    elif ph > 7.5:
        issues.append("pH завищений — підмініть воду частково.")
    if temp < 24:
        issues.append("Температура занадто низька — підігрійте воду.")
    elif temp > 28:
        issues.append("Температура занадто висока — охолодіть воду.")
    if ammonia > 0.25:
        issues.append("Аміак підвищений — зробіть підміну води.")
    if not issues:
        issues.append("Усі параметри в межах норми 👍")

    result = "\n".join(issues)
    await update.message.reply_text(f"💧 Результат аналізу:\n{result}")
    return ConversationHandler.END

async def send_graph(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not os.path.exists(DATA_PATH):
        await update.effective_chat.send_message("Немає збережених даних.")
        return

    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Error reading {DATA_PATH}: {e}")
        await update.effective_chat.send_message("Помилка при читанні даних.")
        return

    records = data.get(user_id, [])
    if not records:
        await update.effective_chat.send_message("Дані не знайдено.")
        return

    now = datetime.datetime.now()
    one_month_ago = now - datetime.timedelta(days=30)
    recent = []
    for r in records:
        try:
            ts = datetime.datetime.fromisoformat(r["timestamp"])
            if ts >= one_month_ago:
                recent.append(r)
        except Exception:
            continue

    data[user_id] = recent
    try:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error writing {DATA_PATH}: {e}")

    if len(recent) < 2:
        await update.effective_chat.send_message("Недостатньо даних для побудови графіків (потрібно хоча б 2 записи).")
        return

    dates = [datetime.datetime.fromisoformat(r["timestamp"]) for r in recent]
    ph_vals = [r["ph"] for r in recent]
    temp_vals = [r["temp"] for r in recent]
    ammonia_vals = [r["ammonia"] for r in recent]

    def make_graph(dates, values, ylabel, title, filename):
        try:
            plt.figure(figsize=(4, 3))
            plt.plot(dates, values, marker='o', color='blue')
            if ylabel == "pH":
                plt.axhline(y=6.5, color='green', linestyle='--', alpha=0.5)
                plt.axhline(y=7.5, color='green', linestyle='--', alpha=0.5)
            elif ylabel == "Температура °C":
                plt.axhline(y=24, color='green', linestyle='--', alpha=0.5)
                plt.axhline(y=28, color='green', linestyle='--', alpha=0.5)
            elif ylabel == "Аміак ppm":
                plt.axhline(y=0.25, color='green', linestyle='--', alpha=0.5)
            plt.title(title)
            plt.xlabel("Дата")
            plt.ylabel(ylabel)
            plt.grid(True)
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(filename, format='png', dpi=80)
            plt.close()
            if not os.path.exists(filename) or os.path.getsize(filename) == 0:
                raise ValueError(f"Failed to save graph: {filename}")
            logger.info(f"Graph saved: {filename}")
        except Exception as e:
            logger.error(f"Error generating graph {filename}: {e}")
            raise

    graph_dir = "data"
    os.makedirs(graph_dir, exist_ok=True)

    paths = {
        "ph": os.path.join(graph_dir, f"graph_ph_{user_id}.png"),
        "temp": os.path.join(graph_dir, f"graph_temp_{user_id}.png"),
        "ammonia": os.path.join(graph_dir, f"graph_ammonia_{user_id}.png"),
    }

    try:
        make_graph(dates, ph_vals, "pH", "Динаміка pH (ост. 30 днів)", paths["ph"])
        make_graph(dates, temp_vals, "Температура °C", "Динаміка температури (ост. 30 днів)", paths["temp"])
        make_graph(dates, ammonia_vals, "Аміак ppm", "Динаміка аміаку (ост. 30 днів)", paths["ammonia"])

        for param, path in paths.items():
            if not os.path.exists(path):
                await update.effective_chat.send_message(f"Помилка: графік {param} не створено.")
                continue
            try:
                with open(path, 'rb') as f:
                    await update.effective_chat.send_photo(
                        photo=InputFile(f, filename=f"{param}.png"),
                        caption=f"📊 {param.capitalize()}"
                    )
            except Exception as e:
                logger.error(f"Error sending {path}: {e}")
                await update.effective_chat.send_message(f"Помилка при відправці графіка {param}: {e}")
            finally:
                if os.path.exists(path):
                    os.remove(path)
                    logger.info(f"Deleted {path}")
    except Exception as e:
        logger.error(f"Error in send_graph: {e}")
        await update.effective_chat.send_message("Помилка при створенні графіків.")
        return ConversationHandler.END

def get_water_conversation_handler():
    return ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^💧 Якість води$"), water_menu)],
        states={
            MENU_CHOICE: [
                CallbackQueryHandler(handle_water_choice),
                MessageHandler(filters.Regex("^💧 Якість води$"), restart_water_menu),
                MessageHandler(filters.TEXT & ~filters.COMMAND, invalid_input),
            ],
            ASK_PH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_ph),
                MessageHandler(filters.Regex("^💧 Якість води$"), restart_water_menu),
                MessageHandler(filters.TEXT & ~filters.COMMAND, invalid_input),
            ],
            ASK_TEMP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_temp),
                MessageHandler(filters.Regex("^💧 Якість води$"), restart_water_menu),
                MessageHandler(filters.TEXT & ~filters.COMMAND, invalid_input),
            ],
            ASK_AMMONIA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, received_ammonia),
                MessageHandler(filters.Regex("^💧 Якість води$"), restart_water_menu),
                MessageHandler(filters.TEXT & ~filters.COMMAND, invalid_input),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(lambda u, c: ConversationHandler.END, pattern="^CANCEL$"),
            MessageHandler(filters.Regex("^💧 Якість води$"), restart_water_menu),
        ]
    )