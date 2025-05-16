#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import random
import os
import asyncio
from datetime import date, datetime, timedelta # Added timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, CallbackQueryHandler

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Configuration for Bot and Admin ---
TOKEN = os.getenv("TOKEN")
ADMIN_USER_ID_STR = os.getenv("ADMIN_USER_ID")
ADMIN_USER_ID = int(ADMIN_USER_ID_STR) if ADMIN_USER_ID_STR else None

# --- State definitions for conversations ---
CHOOSING_TECHNIQUE, SHOWING_TECHNIQUE_DETAIL = range(2)
ASK_QUESTION_STATE = range(1) # For user asking anonymous question
ADMIN_REPLY_STATE = range(1) # For admin replying to anonymous question (new)

# --- Data for features (can be expanded or moved to separate files/DB later) ---
FINAL_DAILY_TIPS = [
    "Найдите 5 минут для глубокого дыхания. Это поможет успокоиться и сосредоточиться.",
    "Запишите три вещи, за которые вы благодарны сегодня. Практика благодарности улучшает настроение.",
    "Сделайте небольшую прогулку на свежем воздухе. Физическая активность полезна для ума и тела.",
    "Позвоните близкому человеку просто так, чтобы поболтать. Социальные связи важны.",
    "Попробуйте новую короткую медитацию. В интернете много бесплатных ресурсов.",
    "Уделите 15 минут хобби, которое приносит вам удовольствие.",
    "Напишите список своих маленьких побед за неделю. Это повысит самооценку.",
    "Практикуйте осознанность: сосредоточьтесь на своих ощущениях здесь и сейчас на пару минут.",
    "Выпейте стакан воды. Иногда обезвоживание влияет на наше самочувствие больше, чем мы думаем.",
    "Улыбнитесь себе в зеркале. Это простой способ поднять настроение.",
    "Высыпайтесь: спите не менее 8 часов в сутки.",
    "Практикуйте медленное дыхание: вдох через нос, выдох через рот.",
    "В стрессовых ситуациях пейте теплую сладкую воду или чай.",
    "Опишите свои ощущения вслух, чтобы успокоиться.",
    "Фокусируйтесь на реальном окружении, перечисляйте предметы вокруг.",
    "Займитесь простой задачей, требующей концентрации, например, мытьем посуды.",
    "Практикуйте глубокое дыхание для расслабления: вдох на 4 счета, выдох на 6.",
    "Ограничьте время, проводимое в социальных сетях, чтобы избежать сравнения.",
    "Начинайте день с благодарности за то, что у вас есть.",
    "Находите поводы для радости каждый день.",
    "Ведите дневник благодарности: записывайте три вещи, за которые вы благодарны.",
    "Планируйте приятные события на день, чтобы было что ждать.",
    "Творите добро: помогайте другим, например, сделайте комплимент.",
    "Выражайте свои эмоции творчески: рисуйте, пишите, танцуйте.",
    "Уделяйте время хобби и увлечениям, которые приносят радость.",
    "Ставьте перед собой маленькие задачи и отмечайте их выполнение.",
    "Любите и цените себя, работайте над самооценкой.",
    "Хвалите себя за достижения, делитесь успехами.",
    "Сравнивайте себя с прошлым собой, а не с другими.",
    "Награждайте себя за достижения, даже маленькие.",
    "Избегайте перфекционизма, принимайте, что ошибки — это часть обучения.",
    "Действуйте уверенно, чтобы вас воспринимали как авторитетного человека.",
    "Учитесь говорить \"нет\" при необходимости, чтобы не перегружаться.",
    "Практикуйте осознанность: фокусируйтесь на дыхании несколько минут в день.",
    "Обсуждайте возникающие проблемы сразу, не накапливайте обиды.",
    "Помогайте другим, это приносит удовлетворение.",
    "Обнимайте близких, физический контакт важен для эмоционального здоровья.",
    "Открыто делитесь своими чувствами с близкими.",
    "Используйте открытую невербалику: не скрещивайте руки, показывайте ладони.",
    "Дарите небольшие подарки, чтобы улучшить отношения.",
    "Общайтесь с друзьями и близкими, поддерживайте социальные связи.",
    "Учитесь прощать себя и других, чтобы не нести груз обид.",
    "Составляйте списки дел и планируйте свой день.",
    "Питайтесь здоровой пищей, избегайте переедания.",
    "Занимайтесь физическими упражнениями регулярно.",
    "Проводите время на природе, это снижает стресс.",
    "Устанавливайте реалистичные цели и разбивайте их на шаги.",
    "Планируйте перерывы в течение дня для отдыха и восстановления.",
    "Применяйте прием \"10 минут\": начните работать над задачей на 10 минут, чтобы преодолеть прокрастинацию.",
    "Помните, что забота о себе — не эгоизм, а необходимость.",
    "Создайте утренний ритуал, который настраивает на позитивный день.",
    "Практикуйте осознанное питание: наслаждайтесь каждым кусочком.",
    "Если чувствуете перегрузку, сделайте короткую прогулку или потянитесь.",
    "Задайте себе вопрос: \"Это действительно правда?\" при появлении навязчивых негативных мыслей.",
    "Воспринимайте неудачу не как поражение, а как ценный урок и возможность для роста.",
    "Сосредоточьтесь на том, что вы можете контролировать, и отпустите остальное.",
    "Устраивайте себе \"цифровой детокс\" – время без гаджетов.",
    "Ищите юмор в повседневных ситуациях. Смех – отличное лекарство от стресса.",
    "Будьте к себе так же добры и сострадательны, как к хорошему другу.",
    "Каждый день старайтесь узнать что-то новое, даже самое маленькое.",
    "Заземлитесь: назовите 3 предмета, которые видите, и 3 звука, которые слышите, чтобы вернуться в \"здесь и сейчас\".",
    "Практикуйте принятие: признавайте свои чувства и мысли без осуждения.",
    "Позвольте себе ничего не делать некоторое время, просто будьте.",
    "Вспомните ситуацию, когда вы успешно справились с трудностями, и ваши сильные качества.",
    "Послушайте музыку, которая поднимает настроение или помогает расслабиться.",
    "Завершайте день рефлексией: подумайте о хорошем и о том, чему научились.",
    "Не бойтесь просить о помощи, когда она вам нужна.",
    "Создайте \"копилку приятных моментов\": записывайте или фотографируйте радостные события.",
    "Определите свои личные границы и учитесь их отстаивать вежливо, но твердо.",
    "Найдите время для тишины и уединения, чтобы побыть наедине с собой."
]

SELF_HELP_TECHNIQUES = {
    "cognitive_restructuring": {
        "menu_name": "Когнитивная реструктуризация (10-15 мин)",
        "details": (
            "**Когнитивная реструктуризация**\n\n"
            "**Описание**: Техника из КПТ, направленная на выявление и изменение автоматических негативных мыслей. "
            "Пользователь записывает мысль, анализирует доказательства за и против и формулирует более сбалансированную мысль.\n\n"
            "**Как это работает (примерный сценарий с ботом)**:\n"
            "1. Бот: «Какая негативная мысль у тебя сейчас преобладает?»\n"
            "2. Вы отвечаете.\n"
            "3. Бот: «Какие факты или доказательства подтверждают эту мысль? А какие ей противоречат или ставят под сомнение?»\n"
            "4. Вы анализируете.\n"
            "5. Бот: «Теперь попробуй сформулировать более сбалансированную, реалистичную мысль на основе этого анализа».\n\n"
            "**Пример**:\n"
            "- Негативная мысль: «Я всегда все порчу».\n"
            "- Сбалансированная мысль: «Иногда я ошибаюсь, но я учусь и часто справляюсь с задачами успешно».\n\n"
            "Эта техника помогает постепенно менять привычные негативные шаблоны мышления.\n"
            "*Интерактивный режим для этой техники будет добавлен позже.*"
        ),
        "interactive_planned": True
    },
    "mindfulness_meditation": {
        "menu_name": "Медитация осознанности (5-10 мин)",
        "details": (
            "**Медитация осознанности**\n\n"
            "**Описание**: Осознанность помогает снизить стресс, фокусируясь на настоящем моменте без осуждения. "
            "Простое упражнение — наблюдение за дыханием.\n\n"
            "**Как практиковать (инструкция от бота)**:\n"
            "1. Бот: «Сядьте удобно, можно закрыть глаза или мягко расфокусировать взгляд».\n"
            "2. Бот: «Направьте внимание на свое дыхание. Почувствуйте, как воздух входит и выходит из вашего тела. Не пытайтесь его контролировать, просто наблюдайте».\n"
            "3. Бот: «Если ваши мысли начинают блуждать (а они будут!), мягко и без осуждения верните внимание обратно к дыханию. Это нормально, это часть практики».\n"
            "4. Бот: «Продолжайте так в течение 5-10 минут».\n\n"
            "**Пример**: Практика 5 минут в день может улучшить концентрацию и снизить тревогу."
        ),
        "interactive_planned": False
    },
    "gratitude_journal": {
        "menu_name": "Дневник благодарности (5 мин)",
        "details": (
            "**Дневник благодарности**\n\n"
            "**Описание**: Ежедневная запись вещей, за которые вы благодарны, улучшает настроение, повышает оптимизм и снижает симптомы депрессии.\n\n"
            "**Как это работает (примерный сценарий с ботом)**:\n"
            "1. Бот (ежедневно или по запросу): «Привет! Давай запишем три вещи, за которые ты благодарен сегодня».\n"
            "2. Вы отвечаете, перечисляя три пункта.\n"
            "3. Бот (опционально): «Отлично! Хочешь немного поразмышлять, почему эти вещи важны для тебя или какие чувства они вызывают?»\n"
            "4. Бот может сохранять ваши записи (эта функция будет добавлена позже), чтобы вы могли к ним вернуться.\n\n"
            "**Пример**:\n"
            "- Благодарность: «За утренний кофе, поддержку друга, интересную книгу».\n\n"
            "Эта простая практика помогает сместить фокус внимания на позитивные аспекты жизни.\n"
            "*Интерактивный режим для этой техники будет добавлен позже.*"
        ),
        "interactive_planned": True
    },
    "behavioral_activation": {
        "menu_name": "Поведенческая активация (15-30 мин)",
        "details": (
            "**Поведенческая активация**\n\n"
            "**Описание**: Планирование и выполнение приятных или значимых для вас активностей помогает преодолеть апатию, повысить уровень энергии и улучшить настроение. Особенно полезно при подавленности или депрессивных состояниях.\n\n"
            "**Как это работает (примерный сценарий с ботом)**:\n"
            "1. Бот: «Давай составим список дел, которые приносят тебе удовольствие или чувство выполненного долга. Это могут быть как большие, так и маленькие дела (например, прогулка, хобби, звонок другу, уборка)»\n"
            "2. Вы составляете список.\n"
            "3. Бот: «Теперь выбери одно или два дела из списка, которые ты мог бы сделать сегодня или завтра. Запланируй их».\n"
            "4. Бот может напомнить о запланированном деле (функция будет добавлена позже).\n"
            "5. Бот (после предполагаемого времени выполнения): «Удалось ли тебе сделать запланированное? Как ты себя чувствуешь после этого?»\n\n"
            "**Пример**: Активность — 30-минутная прогулка в парке. Результат — чувство бодрости и улучшение настроения.\n"
            "*Интерактивный режим для этой техники будет добавлен позже.*"
        ),
        "interactive_planned": True
    },
    "progressive_muscle_relaxation": {
        "menu_name": "Прогрессивная мышечная релаксация (10-15 мин)",
        "details": (
            "**Прогрессивная мышечная релаксация (ПМР)**\n\n"
            "**Описание**: Эта техника заключается в последовательном напряжении и расслаблении различных групп мышц. Это помогает лучше осознавать мышечное напряжение и достигать глубокого физического и эмоционального расслабления.\n\n"
            "**Как практиковать (инструкция от бота)**:\n"
            "1. Бот: «Сядьте или лягте удобно. Закройте глаза. Дышите медленно и спокойно».\n"
            "2. Бот: «Начнем с мышц стоп и голеней. Сильно напрягите их на 5-7 секунд, как бы сжимая... А теперь полностью расслабьте на 10-15 секунд. Почувствуйте разницу».\n"
            "3. Бот: «Теперь мышцы бедер. Напрягите их... Расслабьте...».\n"
            "4. Бот последовательно проведет вас через другие группы мышц: живот, грудь, спина, кисти и предплечья, плечи, шея, лицо (лоб, глаза, челюсти).\n"
            "5. Бот: «Завершите практику, почувствовав полное расслабление во всем теле. Побудьте в этом состоянии несколько минут».\n\n"
            "**Пример**: Практика ПМР перед сном может значительно улучшить качество сна.\n"
            "*Интерактивное ведение по шагам (например, с таймерами) будет добавлено позже.*"
        ),
        "interactive_planned": False 
    },
    "deep_breathing": {
        "menu_name": "Глубокое дыхание (5 мин)",
        "details": (
            "**Глубокое дыхание (Диафрагмальное дыхание)**\n\n"
            "**Описание**: Медленное, глубокое дыхание с акцентом на работу диафрагмы помогает активировать парасимпатическую нервную систему, отвечающую за расслабление. Это быстрый способ снизить уровень стресса и тревоги.\n\n"
            "**Как практиковать (инструкция от бота)**:\n"
            "1. Бот: «Сядьте или лягте удобно. Положите одну руку на грудь, другую на живот».\n"
            "2. Бот: «Медленно вдохните через нос так, чтобы рука на животе поднялась, а рука на груди осталась почти неподвижной. Считайте мысленно до 4 во время вдоха».\n"
            "3. Бот: «Задержите дыхание на 2-4 секунды (если комфортно)».\n"
            "4. Бот: «Медленно выдохните через рот (или нос), чувствуя, как живот опускается. Старайтесь, чтобы выдох был немного длиннее вдоха, например, считайте до 6».\n"
            "5. Бот: «Повторите этот цикл 5-10 раз или в течение нескольких минут».\n\n"
            "**Пример**: Используйте эту технику при внезапном приступе тревоги, перед важным событием или просто для ежедневного расслабления.\n"
            "*Интерактивное ведение по шагам (например, с таймерами) будет добавлено позже.*"
        ),
        "interactive_planned": False 
    },
    "self_compassion_exercises": {
        "menu_name": "Упражнения на самосострадание (5-10 мин)",
        "details": (
            "**Упражнения на самосострадание**\n\n"
            "**Описание**: Самосострадание — это умение относиться к себе с такой же добротой, пониманием и поддержкой, какие вы проявили бы к хорошему другу в трудной ситуации. Это помогает снизить самокритику и справиться с негативными эмоциями.\n\n"
            "**Как практиковать (примеры сценариев с ботом)**:\n"
            "1.  **Поддерживающее письмо себе**:\n"
            "    *   Бот: «Представьте, что ваш близкий друг переживает то же, что и вы сейчас, и испытывает похожие чувства. Что бы вы ему сказали? Какие слова поддержки и понимания вы бы нашли? Напишите это в виде короткого письма или сообщения».\n"
            "    *   Бот: «А теперь перечитайте это, но уже как будто это адресовано вам».\n"
            "2.  **Поддерживающие фразы (аффирмации самосострадания)**:\n"
            "    *   Бот: «Выберите или придумайте несколько фраз, которые откликаются вам, и повторяйте их в трудные моменты. Например:\n"
            "        *   ‘Это трудный момент, и я делаю все, что могу’.\n"
            "        *   ‘Я заслуживаю доброты и понимания, даже когда ошибаюсь’.\n"
            "        *   ‘Страдания – это часть человеческого опыта, я не одинок(а) в этом’.\n"
            "        *   ‘Я могу быть добр(а) к себе в этой ситуации’.\n\n"
            "**Пример**: Вместо самобичевания «Я неудачник», сказать себе: «Мне сейчас тяжело, и это нормально. Я постараюсь себя поддержать».\n"
            "*Интерактивный режим для этих упражнений будет добавлен позже.*"
        ),
        "interactive_planned": True
    }
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
        rf"Привет, {user.mention_html()}! Я твой личный помощник по ментальному здоровью. Чем могу помочь?",
        reply_markup=get_main_keyboard(),
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "**Основные команды и функции бота:**\n\n"
        "- **Получить совет дня ✨**: Ежедневный совет для поддержки вашего настроения и благополучия.\n"
        "- **Пройти тест 📝**: Различные тесты для самодиагностики (например, на уровень стресса, тревоги). *Раздел в разработке*\n"
        "- **Техники самопомощи 🧘**: Практические упражнения для снятия стресса, релаксации и улучшения эмоционального состояния.\n"
        "- **Записать настроение/привычку 😊**: Возможность отслеживать свое настроение или формирование полезных привычек. *Раздел в разработке*\n"
        "- **Задать анонимный вопрос ❓**: Вы можете анонимно задать вопрос администратору канала @psihotips. Ответ может прийти через бота или быть опубликован на канале.\n"
        "- **Помощь / О боте ℹ️**: Информация о боте и его возможностях.\n\n"
        "Для навигации используйте кнопки внизу экрана. Если кнопки исчезли, введите команду /start."
    )
    await update.message.reply_text(help_text, parse_mode='Markdown', reply_markup=get_main_keyboard())

# --- Daily Tip Feature ---
async def get_daily_tip(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    today_str = date.today().isoformat()

    # Initialize user_data if not present
    if 'last_tip_date' not in context.user_data:
        context.user_data['last_tip_date'] = ''
    if 'given_tips_indices' not in context.user_data:
        context.user_data['given_tips_indices'] = []

    if context.user_data['last_tip_date'] == today_str:
        await update.message.reply_text("Вы уже получили свой совет на сегодня. Новый совет будет доступен завтра!", reply_markup=get_main_keyboard())
        return

    available_tips_indices = [i for i, _ in enumerate(FINAL_DAILY_TIPS) if i not in context.user_data['given_tips_indices']]

    if not available_tips_indices:
        # All tips have been shown, reset for the user
        context.user_data['given_tips_indices'] = []
        available_tips_indices = list(range(len(FINAL_DAILY_TIPS)))
        if not available_tips_indices: # Should not happen if FINAL_DAILY_TIPS is not empty
             await update.message.reply_text("К сожалению, советы закончились. Загляните позже!", reply_markup=get_main_keyboard())
             return

    chosen_tip_index = random.choice(available_tips_indices)
    tip = FINAL_DAILY_TIPS[chosen_tip_index]
    
    context.user_data['given_tips_indices'].append(chosen_tip_index)
    context.user_data['last_tip_date'] = today_str

    await update.message.reply_text(f"✨ **Совет дня для вас:**\n\n{tip}", parse_mode='Markdown', reply_markup=get_main_keyboard())

# --- Self-Help Techniques Feature ---
async def self_help_techniques_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    buttons = []
    for key, technique in SELF_HELP_TECHNIQUES.items():
        buttons.append([InlineKeyboardButton(technique["menu_name"], callback_data=f"technique_{key}")])
    
    buttons.append([InlineKeyboardButton("<< Назад в главное меню", callback_data="technique_back_to_main")])
    reply_markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("Выберите технику самопомощи:", reply_markup=reply_markup)
    return CHOOSING_TECHNIQUE

async def self_help_technique_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    technique_key = query.data.split("_")[-1]

    if technique_key == "back": # Back from detail to list
        buttons = []
        for key, technique_info in SELF_HELP_TECHNIQUES.items():
            buttons.append([InlineKeyboardButton(technique_info["menu_name"], callback_data=f"technique_{key}")])
        buttons.append([InlineKeyboardButton("<< Назад в главное меню", callback_data="technique_back_to_main")])
        reply_markup = InlineKeyboardMarkup(buttons)
        await query.edit_message_text("Выберите технику самопомощи:", reply_markup=reply_markup)
        return CHOOSING_TECHNIQUE
    elif technique_key == "main": # Back to main menu from list
        await query.edit_message_text("Вы вернулись в главное меню.", reply_markup=None) # Remove inline keyboard
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Главное меню",reply_markup=get_main_keyboard()) # Show main keyboard
        return ConversationHandler.END

    technique = SELF_HELP_TECHNIQUES.get(technique_key)
    if technique:
        details = technique["details"]
        # Add a 'Back' button to the details view
        back_button = InlineKeyboardMarkup([[
            InlineKeyboardButton("<< Назад к списку техник", callback_data="technique_detail_back")
        ]])
        await query.edit_message_text(text=details, parse_mode='Markdown', reply_markup=back_button)
        return SHOWING_TECHNIQUE_DETAIL 
    else:
        await query.edit_message_text("Техника не найдена. Пожалуйста, выберите из списка.")
        return CHOOSING_TECHNIQUE # Stay in the same state

async def self_help_technique_detail_back(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    # This is essentially the same as self_help_technique_chosen with callback_data="technique_back"
    buttons = []
    for key, technique_info in SELF_HELP_TECHNIQUES.items():
        buttons.append([InlineKeyboardButton(technique_info["menu_name"], callback_data=f"technique_{key}")])
    buttons.append([InlineKeyboardButton("<< Назад в главное меню", callback_data="technique_back_to_main")])
    reply_markup = InlineKeyboardMarkup(buttons)
    await query.edit_message_text("Выберите технику самопомощи:", reply_markup=reply_markup)
    return CHOOSING_TECHNIQUE

async def self_help_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Выход из раздела техник самопомощи.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

# --- Anonymous Question Feature ---
async def ask_anonymous_question_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Пожалуйста, напишите ваш вопрос. Он будет анонимно отправлен администратору канала @psihotips. "
        "Чтобы отменить, введите /cancel."
    )
    return ASK_QUESTION_STATE

async def ask_anonymous_question_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    question_text = update.message.text
    original_user_id = update.message.from_user.id

    if ADMIN_USER_ID:
        try:
            reply_button_callback_data = f"admin_reply_to_{original_user_id}"
            logger.info(f"Setting callback_data for admin reply button: {reply_button_callback_data}")
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("Ответить пользователю", callback_data=reply_button_callback_data)]
            ])

            await context.bot.send_message(
                chat_id=ADMIN_USER_ID,
                text=f"Новый анонимный вопрос от пользователя (ID: {original_user_id}):\n\n\"{question_text}\"",
                reply_markup=keyboard
            )
            await update.message.reply_text("Ваш вопрос анонимно отправлен администратору. Ожидайте, возможно, он ответит вам через бота.", reply_markup=get_main_keyboard())
        except Exception as e:
            logger.error(f"Failed to send anonymous question to admin: {e}")
            await update.message.reply_text("Произошла ошибка при отправке вопроса администратору. Пожалуйста, попробуйте позже.", reply_markup=get_main_keyboard())
    else:
        await update.message.reply_text("Функция анонимных вопросов временно недоступна, так как не настроен администратор.", reply_markup=get_main_keyboard())
    
    return ConversationHandler.END

async def cancel_anonymous_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отправка анонимного вопроса отменена.", reply_markup=get_main_keyboard())
    return ConversationHandler.END

# --- Admin Reply to Anonymous Question Handlers (NEW) ---
async def admin_start_reply_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    callback_data = query.data
    logger.info(f"Admin reply button pressed. Callback data: {callback_data}")

    try:
        original_user_id = int(callback_data.split("_")[-1])
        context.user_data['admin_reply_target_user_id'] = original_user_id
        
        original_question_text = query.message.text
        await query.edit_message_text(
            text=f"{original_question_text}\n\n---\n📝 Введите ваш ответ для пользователя ID {original_user_id}. Следующее ваше сообщение будет отправлено ему.\nИли отправьте /cancel_admin_reply для отмены."
        )
        return ADMIN_REPLY_STATE
    except (IndexError, ValueError) as e:
        logger.error(f"Error parsing callback_data for admin reply: {callback_data}, error: {e}")
        await query.edit_message_text(text=f"{query.message.text}\n\n---\n❌ Ошибка: не удалось определить пользователя для ответа. Попробуйте снова.")
        return ConversationHandler.END

async def admin_process_reply_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.effective_user.id != ADMIN_USER_ID:
        return ConversationHandler.END 

    admin_reply_text = update.message.text
    target_user_id = context.user_data.get('admin_reply_target_user_id')

    if not target_user_id:
        await update.message.reply_text("Произошла ошибка: не найден ID пользователя для ответа. Пожалуйста, начните процесс ответа снова через кнопку 'Ответить'.")
        return ConversationHandler.END

    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=f"💬 Ответ от администратора на ваш анонимный вопрос:\n\n\"{admin_reply_text}\""
        )
        await update.message.reply_text("✅ Ваш ответ успешно отправлен пользователю.")
    except Exception as e:
        logger.error(f"Failed to send admin reply to user {target_user_id}: {e}")
        await update.message.reply_text(f"❌ Не удалось отправить ответ пользователю ID {target_user_id}. Возможно, пользователь заблокировал бота или произошла другая ошибка.")
    
    context.user_data.pop('admin_reply_target_user_id', None)
    return ConversationHandler.END

async def admin_cancel_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Отправка ответа отменена.")
    context.user_data.pop('admin_reply_target_user_id', None)
    return ConversationHandler.END

# --- Generic Message Handler (for non-command text) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # This function can be used for more general text handling if needed
    # For now, most text interactions are covered by ConversationHandlers or specific command handlers
    # If a message is not caught by any other handler, it might end up here.
    # We can add a generic reply or ignore.
    # logger.info(f"Unhandled message received: {update.message.text}")
    # await update.message.reply_text("Не совсем понял вас. Пожалуйста, используйте кнопки меню или команды.", reply_markup=get_main_keyboard())
    pass # Or a more specific action

# --- Main Bot Setup ---
def main() -> None:
    if not TOKEN:
        logger.error("TOKEN environment variable not set!")
        return
    if not ADMIN_USER_ID:
        logger.warning("ADMIN_USER_ID environment variable not set! Some admin features might not work.")

    application = Application.builder().token(TOKEN).build()

    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.Regex("^Помощь / О боте ℹ️$"), help_command))

    # Daily Tip handler
    application.add_handler(MessageHandler(filters.Regex("^Получить совет дня ✨$"), get_daily_tip))

    # Self-Help Techniques conversation handler
    self_help_conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Техники самопомощи 🧘$"), self_help_techniques_start)],
        states={
            CHOOSING_TECHNIQUE: [
                CallbackQueryHandler(self_help_technique_chosen, pattern="^technique_.+$")
            ],
            SHOWING_TECHNIQUE_DETAIL: [
                CallbackQueryHandler(self_help_technique_detail_back, pattern="^technique_detail_back$")
            ],
        },
        fallbacks=[CommandHandler("cancel", self_help_cancel)],
    )
    application.add_handler(self_help_conv_handler)

    # Anonymous Question conversation handler
    ask_anonymous_question_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^Задать анонимный вопрос ❓$"), ask_anonymous_question_entry)],
        states={
            ASK_QUESTION_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_anonymous_question_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel_anonymous_question)],
    )
    application.add_handler(ask_anonymous_question_conv)

    # Admin Reply to Anonymous Question conversation handler (NEW)
    admin_reply_conversation_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_start_reply_flow, pattern="^admin_reply_to_\d+$")],
        states={
            ADMIN_REPLY_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_process_reply_message)],
        },
        fallbacks=[CommandHandler("cancel_admin_reply", admin_cancel_reply)],
    )
    application.add_handler(admin_reply_conversation_handler)

    # Generic message handler (must be added last)
    # application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Bot starting...")
    application.run_polling()

if __name__ == "__main__":
    main()

