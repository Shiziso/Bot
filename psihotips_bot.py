#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import random
import os
import threading # Added for running bot in a separate thread
from flask import Flask # Added for Render Web Service
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration for Bot and Admin ---
TOKEN = os.getenv("TOKEN") # Get TOKEN from environment variable
ADMIN_USER_ID_STR = os.getenv("ADMIN_USER_ID") # Get ADMIN_USER_ID from environment variable
ADMIN_USER_ID = int(ADMIN_USER_ID_STR) if ADMIN_USER_ID_STR else None

# --- Flask App for Render Web Service ---
flask_app = Flask(__name__)

@flask_app.route('/')
def hello_world():
    return 'Telegram Bot is running!'

# --- Data for features (can be expanded or moved to separate files/DB later) ---
DAILY_TIPS = [
    "Найдите 5 минут для глубокого дыхания. Это поможет успокоиться и сосредоточиться.",
    "Запишите три вещи, за которые вы благодарны сегодня. Практика благодарности улучшает настроение.",
    "Сделайте небольшую прогулку на свежем воздухе. Физическая активность полезна для ума и тела.",
    "Позвоните близкому человеку просто так, чтобы поболтать. Социальные связи важны.",
    "Попробуйте новую короткую медитацию. В интернете много бесплатных ресурсов.",
    "Уделите 15 минут хобби, которое приносит вам удовольствие.",
    "Напишите список своих маленьких побед за неделю. Это повысит самооценку.",
    "Практикуйте осознанность: сосредоточьтесь на своих ощущениях здесь и сейчас на пару минут.",
    "Выпейте стакан воды. Иногда обезвоживание влияет на наше самочувствие больше, чем мы думаем.",
    "Улыбнитесь себе в зеркале. Это простой способ поднять настроение."
]

SELF_HELP_TECHNIQUES = {
    "дыхание": "**Техника диафрагмального дыхания:**\n1. Сядьте или лягте в удобное положение.\n2. Положите одну руку на грудь, другую на живот.\n3. Медленно вдохните через нос, стараясь, чтобы живот поднялся, а грудь оставалась почти неподвижной.\n4. Медленно выдохните через рот, чувствуя, как живот опускается.\n5. Повторяйте в течение 5-10 минут.",
    "релаксация": "**Техника прогрессивной мышечной релаксации:**\n1. Сядьте или лягте удобно.\n2. Начните с пальцев ног: сильно напрягите их на 5 секунд, затем полностью расслабьте на 10-15 секунд. Обратите внимание на разницу в ощущениях.\n3. Постепенно продвигайтесь вверх по телу (икры, бедра, живот, грудь, руки, плечи, шея, лицо), напрягая и расслабляя каждую группу мышц.\n4. Завершите, почувствовав полное расслабление во всем теле.",
    "заземление": "**Техника заземления '5-4-3-2-1':**\nКогда чувствуете тревогу, попробуйте найти вокруг себя:\n- 5 вещей, которые вы видите (например, стол, цветок, ручка, окно, книга).\n- 4 вещи, которые вы можете потрогать (например, ткань одежды, гладкая поверхность стола, тепло чашки, свои волосы).\n- 3 вещи, которые вы слышите (например, пение птиц, шум машин, тиканье часов).\n- 2 вещи, которые вы можете понюхать (например, запах кофе, свежий воздух, духи).\n- 1 вещь, которую вы можете попробовать на вкус (например, мятная конфета, вода, фрукт)."
}

# --- Helper Functions ---
def get_main_keyboard():
    keyboard = [
        [KeyboardButton("Получить совет дня ✨")],
        [KeyboardButton("Пройти тест 📝"), KeyboardButton("Техники самопомощи 🧘")],
        [KeyboardButton("Записать настроение/привычку 😊"), KeyboardButton("Задать анонимный вопрос ❓")],
        [KeyboardButton("Помощь / О боте ℹ️")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

# --- Command Handlers ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await update.message.reply_html(
        f"Привет, {user.mention_html()}! 👋\n\nЯ ваш помощник по психологической поддержке. Готов помочь вам советом, предложить тест или технику самопомощи. Выберите действие на клавиатуре ниже.",
        reply_markup=get_main_keyboard()
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "**Доступные команды и функции:**\n\n"
        "🔹 **Получить совет дня ✨** - Случайный совет для поддержки.\n"
        "🔹 **Пройти тест 📝** - Короткие психологические тесты (в разработке).\n"
        "🔹 **Техники самопомощи 🧘** - Инструкции к техникам релаксации и др.\n"
        "🔹 **Записать настроение/привычку 😊** - Отслеживайте свое состояние (в разработке).\n"
        "🔹 **Задать анонимный вопрос ❓** - Анонимно спросите специалиста.\n"
        "🔹 **/start** - Начало работы с ботом.\n"
        "🔹 **/help** - Показать это сообщение.\n\n"
        "Канал автора: @psihotips"
    )
    await update.message.reply_text(help_text, reply_markup=get_main_keyboard(), parse_mode='Markdown')

async def daily_tip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    tip = random.choice(DAILY_TIPS)
    await update.message.reply_text(f"✨ **Совет дня:**\n\n{tip}", parse_mode='Markdown', reply_markup=get_main_keyboard())

# --- Feature: Anonymous Questions ---
ASK_QUESTION_STATE = 1

async def ask_anonymous_question_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if not ADMIN_USER_ID:
        await update.message.reply_text("Функция анонимных вопросов временно недоступна, так как не настроен ID администратора.", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    await update.message.reply_text(
        "Пожалуйста, напишите ваш вопрос. Он будет отправлен администратору анонимно. \nЧтобы отменить, введите /cancel.",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("/cancel")]], resize_keyboard=True, one_time_keyboard=True)
    )
    return ASK_QUESTION_STATE

async def process_anonymous_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_question = update.message.text
    user_info = update.effective_user
    
    if not ADMIN_USER_ID:
        await update.message.reply_text("Не удалось отправить вопрос: не настроен ID администратора.", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    try:
        await context.bot.send_message(
            chat_id=ADMIN_USER_ID,
            text=f"❓ Новый анонимный вопрос:\n\n{user_question}\n\n(ID пользователя для возможного ответа через бота, если потребуется: {user_info.id})"
        )
        await update.message.reply_text(
            "Спасибо! Ваш вопрос был анонимно отправлен администратору.",
            reply_markup=get_main_keyboard()
        )
    except Exception as e:
        logger.error(f"Failed to send anonymous question to admin: {e}")
        await update.message.reply_text(
            "Произошла ошибка при отправке вашего вопроса. Пожалуйста, попробуйте позже.",
            reply_markup=get_main_keyboard()
        )
    return ConversationHandler.END

async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Действие отменено.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

# --- Feature: Self-Help Techniques ---
async def self_help_techniques_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    buttons = [[InlineKeyboardButton(name.capitalize(), callback_data=f"technique_{key}")] for key, name in SELF_HELP_TECHNIQUES.items()]
    buttons.append([InlineKeyboardButton("🔙 Назад в меню", callback_data="technique_main_menu")])
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Выберите технику самопомощи:", reply_markup=reply_markup)

async def self_help_technique_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    if query.data is None or not isinstance(query.data, str):
        logger.warning(f"Received unexpected callback_data: {query.data}")
        if query.message:
            await query.edit_message_text(text="Произошла ошибка. Попробуйте еще раз.")
            await context.bot.send_message(chat_id=query.message.chat_id, text="Что дальше?", reply_markup=get_main_keyboard())
        return

    parts = query.data.split('_', 1)
    action = parts[0]
    key = parts[1] if len(parts) > 1 else None

    if action == "technique" and key == "main_menu":
        if query.message:
            await query.edit_message_text("Вы вернулись в главное меню.", reply_markup=None)
            await context.bot.send_message(chat_id=query.message.chat_id, text="Выберите действие:", reply_markup=get_main_keyboard())
        return
    elif action == "technique" and key in SELF_HELP_TECHNIQUES:
        technique_text = SELF_HELP_TECHNIQUES.get(key)
        if query.message:
            await query.edit_message_text(text=technique_text, parse_mode='Markdown', reply_markup=None)
            await context.bot.send_message(chat_id=query.message.chat_id, text="Что дальше?", reply_markup=get_main_keyboard())
    else:
        if query.message:
            await query.edit_message_text(text="Извините, информация по этой технике не найдена или произошла ошибка.")
            await context.bot.send_message(chat_id=query.message.chat_id, text="Что дальше?", reply_markup=get_main_keyboard())

# --- Feature: Psychological Tests (Placeholder) ---
async def tests_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Раздел с психологическими тестами находится в разработке. Следите за обновлениями!", reply_markup=get_main_keyboard())

# --- Feature: Mood/Habit Tracker (Placeholder) ---
async def mood_tracker_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Функция трекера настроения и привычек пока в разработке. Скоро будет доступна!", reply_markup=get_main_keyboard())

# --- Message Handler for Keyboard Buttons ---
async def handle_keyboard_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    text = update.message.text
    if text == "Получить совет дня ✨":
        await daily_tip_command(update, context)
    elif text == "Пройти тест 📝":
        await tests_command(update, context)
    elif text == "Техники самопомощи 🧘":
        await self_help_techniques_menu(update, context)
    elif text == "Записать настроение/привычку 😊":
        await mood_tracker_command(update, context)
    elif text == "Помощь / О боте ℹ️":
        await help_command(update, context)

# --- Telegram Bot Application Setup ---
def run_telegram_bot():
    if not TOKEN:
        logger.error("Telegram TOKEN not found in environment variables!")
        return
    if not ADMIN_USER_ID:
        logger.warning("ADMIN_USER_ID not found or invalid in environment variables! Anonymous questions might not work.")

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("daily_tip", daily_tip_command))
    application.add_handler(CommandHandler("tests", tests_command))
    application.add_handler(CommandHandler("mood_tracker", mood_tracker_command))
    application.add_handler(CommandHandler("techniques", self_help_techniques_menu))

    conv_handler_anonymous_question = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex('^Задать анонимный вопрос ❓$'), ask_anonymous_question_start), CommandHandler('ask', ask_anonymous_question_start)],
        states={
            ASK_QUESTION_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_anonymous_question)],
        },
        fallbacks=[CommandHandler("cancel", cancel_conversation)],
    )
    application.add_handler(conv_handler_anonymous_question)
    application.add_handler(CallbackQueryHandler(self_help_technique_callback, pattern='^technique_'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_keyboard_buttons))

    logger.info("Telegram Bot is starting polling...")
    application.run_polling()

# --- Main Execution ---
if __name__ == "__main__":
    # Start Telegram bot in a new thread
    bot_thread = threading.Thread(target=run_telegram_bot)
    bot_thread.start()
    
    # Start Flask web server for Render
    port = int(os.environ.get("PORT", 5000)) # Render provides PORT, default to 5000 for local testing
    logger.info(f"Flask app starting on port {port}")
    flask_app.run(host='0.0.0.0', port=port)


