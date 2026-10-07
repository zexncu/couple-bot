import asyncio
import random
import string
import sqlite3
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# --- НАСТРОЙКА ---
BOT_TOKEN = "8880847718:AAF8ioJVP45Dqz83ZoI7O-qaEtwaHc9aDgo"  # ⚠️ Укажите ваш токен от @BotFather в кавычках

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("couple_bot.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            pair_code TEXT,
            partner_id INTEGER,
            mood TEXT DEFAULT 'Не указано',
            points INTEGER DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS couples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER,
            user2_id INTEGER,
            start_date TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS wishes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            wish_text TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS places (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            place_name TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS time_capsules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender_id INTEGER,
            receiver_id INTEGER,
            message_text TEXT,
            deliver_date TEXT,
            is_delivered INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()

init_db()

TASKS = [
    "Приготовить сегодня вместе ужин 🍳",
    "Сделать партнёру массаж спины в течение 15 минут 💆‍♂️💆‍♀️",
    "Устроить вечер без телефонов и просто поговорить по душам 📵",
    "Написать партнёру 5 причин, почему вы его любите 📝",
    "Включить любимую музыку и потанцевать прямо посреди комнаты 💃🕺"
]

DAILY_QUESTIONS = [
    "Какое твоё самое яркое воспоминание, связанное со мной? 🥰",
    "Если бы мы могли прямо сейчас улететь в любую точку мира, куда бы мы отправились? ✈️",
    "Какая моя привычка кажется тебе самой милой? 😊",
    "Какое свидание из всех, что у нас были, тебе запомнилось больше всего? 🗓️"
]

QUIZ_QUESTIONS = [
    {"q": "Какой мой любимый цвет?", "a": ["Синий", "Красный", "Черный", "Зеленый"]},
    {"q": "Какое блюдо я больше всего люблю?", "a": ["Пицца", "Суши", "Борщ", "Паста"]},
    {"q": "Где бы я хотел(а) провести идеальный отпуск?", "a": ["В горах", "На море", "В мегаполисе", "Дома под пледом"]}
]

class BotStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_wish = State()
    waiting_for_place = State()
    waiting_for_capsule_date = State()
    waiting_for_capsule_text = State()

def get_user(user_id):
    conn = sqlite3.connect("couple_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def get_main_menu():
    builder = ReplyKeyboardBuilder()
    builder.button(text="📅 Счётчик дней")
    builder.button(text="😊 Настроение")
    builder.button(text="🎲 Задание для двоих")
    builder.button(text="🧠 Викторина")
    builder.button(text="❓ Вопрос дня")
    builder.button(text="⭐ Желания")
    builder.button(text="📍 Места")
    builder.button(text="⏳ Капсула времени")
    builder.button(text="📊 Статистика")
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    username = message.from_user.username or message.from_user.first_name
    user = get_user(user_id)
    
    conn = sqlite3.connect("couple_bot.db")
    cursor = conn.cursor()
    if not user:
        my_code = generate_code()
        cursor.execute("INSERT INTO users (user_id, username, pair_code) VALUES (?, ?, ?)", (user_id, username, my_code))
        conn.commit()
    conn.close()
    
    user = get_user(user_id)
    if user and user[3]:
        await message.answer("❤️ Вы уже состоите в паре!", reply_markup=get_main_menu())
    else:
        await message.answer(f"Привет 🥰\n\nЧтобы связать аккаунты:\n1️⃣ Отправь этот код половинке: `{user[2]}`\n2️⃣ Или отправь мне код партнёра в чат.", parse_mode="Markdown")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "📌 **Меню кнопок:**\n"
        "• 📅 Счётчик дней — Сколько вы вместе\n"
        "• 😊 Настроение — Поделиться эмоциями\n"
        "• 🎲 Задание для двоих — Квесты на очки\n"
        "• 🧠 Викторина — Квизы друг для друга\n"
        "• ❓ Вопрос дня — Темы для разговоров\n"
        "• ⭐ Желания / 📍 Места — Общие списки\n"
        "• ⏳ Капсула времени — Письма в будущее\n"
        "• 📊 Статистика — Очки пары\n\n"
        "💔 /unlink — Разорвать связь"
    )
    await message.answer(help_text, parse_mode="Markdown")

@dp.message(F.text.len() == 6, ~F.text.startswith("/"))
async def process_pair_code(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    code = message.text.upper()
    user = get_user(user_id)
    if user and user[3]:
        await message.answer("Вы уже в паре!")
        return
    conn = sqlite3.connect("couple_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE pair_code = ? AND user_id != ?", (code, user_id))
    partner = cursor.fetchone()
    if partner:
        partner_id = partner[0]
        cursor.execute("UPDATE users SET partner_id = ? WHERE user_id = ?", (partner_id, user_id))
        cursor.execute("UPDATE users SET partner_id = ? WHERE user_id = ?", (user_id, partner_id))
        conn.commit()
        conn.close()
        await state.set_state(BotStates.waiting_for_date)
        await message.answer("🎉 Связь успешна!\nВведите дату начала отношений в формате `ДД.ММ.ГГГГ` (напр. `15.08.2024`):")
        try: await bot.send_message(partner_id, "🎉 Вы связаны! Ожидаем ввод даты отношений партнёром.")
        except Exception: pass
    else:
        conn.close()
        await message.answer("❌ Код не найден.")

@dp.message(BotStates.waiting_for_date)
async def process_date(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
        user = get_user(message.from_user.id)
        partner_id = user[3]
        conn = sqlite3.connect("couple_bot.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO couples (user1_id, user2_id, start_date) VALUES (?, ?, ?)", (message.from_user.id, partner_id, message.text))
        conn.commit()
        conn.close()
        await state.clear()
        await message.answer("❤️ Дата сохранена!", reply_markup=get_main_menu())
        if partner_id:
            try: await bot.send_message(partner_id, f"❤️ Дата начала ваших отношений установлена: {message.text}!", reply_markup=get_main_menu())
            except Exception: pass
    except ValueError:
        await message.answer("❌ Неверный формат. Напишите строго ДД.ММ.ГГГГ:")

@dp.message(F.text == "📅 Счётчик дней")
async def cmd_status(message: types.Message):
    user = get_user(message.from_user.id)
    if not user or not user[3]: return
    conn = sqlite3.connect("couple_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT start_date FROM couples WHERE user1_id = ? OR user2_id = ?", (message.from_user.id, message.from_user.id))
    row = cursor.fetchone()
    conn.close()
    if row:
        days = (datetime.now() - datetime.strptime(row[0], "%d.%m.%Y")).days
        await message.answer(f"📅 Вы вместе уже **{max(0, days)}** дней! 🥰 (с {row[0]})", parse_mode="Markdown")

@dp.message(F.text == "😊 Настроение")
async def cmd_mood(message: types.Message):
    builder = InlineKeyboardBuilder()
    for m in ["🥰 Отлично", "😐 Нормально", "😢 Грустно", "😡 Злюсь", "😴 Устал(а)"]:
        builder.button(text=m, callback_data=f"m_{m}")
    builder.adjust(2)
    await message.answer("Какое у тебя сейчас настроение?", reply_markup=builder.as_markup())

@dp.callback_query(F.data.startswith("m_"))
async def process_mood(callback: types.CallbackQuery):
    mood_text = callback.data.replace("m_", "")
    conn = sqlite3.connect("couple_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET mood = ? WHERE user_id = ?", (mood_text, callback.from_user.id))
    conn.commit()
    conn.close()
    await callback.answer("Настроение обновлено!")
    await callback.message.edit_text(f"Твой статус настроения: **{mood_text}**", parse_mode="Markdown")
    user = get_user(callback.from_user.id)
    if user and user[3]:
        try: await bot.send_message(user[3], f"😊 Настроение твоей половинки изменилось на: **{mood_text}**", parse_mode="Markdown")
        except Exception: pass

@dp.message(F.text == "🎲 Задание для двоих")
async def cmd_task(message: types.Message):
    user = get_user(message.from_user.id)
    if not user or not user[3]: return
    task = random.choice(TASKS)
    builder = InlineKeyboardBuilder().button(text="✅ Выполнено! (+10 очков)", callback_data="task_done")
    await message.answer(f"🎲 **Задание для пары:**\n\n{task}", parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "task_done")
async def process_task_done(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user or not user[3]: return
    conn = sqlite3.connect("couple_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET points = points + 10 WHERE user_id IN (?, ?)", (callback.from_user.id, user[3]))
    conn.commit()
    conn.close()
    await callback.answer("Очки начислены!")
    await callback.message.edit_text("🎉 Задание выполнено! Вам обоим начислено по +10 очков.")
    try: await bot.send_message(user[3], "🎉 Половинка отметила задание выполненным! +10 очков пары.")
    except Exception: pass

@dp.message(F.text == "🧠 Викторина")
async def cmd_quiz(message: types.Message):
    user = get_user(message.from_user.id)
    if not user or not user[3]: return
    q_data = random.choice(QUIZ_QUESTIONS)
    options = q_data["a"].copy()
    random.shuffle(options)
    correct_id = options.index(q_data["a"][0])
    await bot.send_poll(
        chat_id=message.chat.id,
        question=f"🧠 Ответь сам(а), а бот пришлет этот же квиз половинке:\n\n{q_data['q']}",
        options=options,
        type="quiz",
        correct_option_id=correct_id,
        is_anonymous=False
    )
    try:
        await bot.send_poll(
            chat_id=user[3],
            question=f"🧠 Твоя половинка запустила викторину! Угадай верный вариант:\n\n{q_data['q']}",
            options=options,
            type="quiz",
            correct_option_id=correct_id,
            is_anonymous=False
        )
    except Exception: pass

@dp.message(F.text == "❓ Вопрос дня")
async def cmd_question(message: types.Message):
    q = random.choice(DAILY_QUESTIONS)
    await message.answer(f"❓ **Вопрос для вашей пары:**\n\n{q}", parse_mode="Markdown")

async def send_daily_question_job():
    conn = sqlite3.connect("couple_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT user1_id, user2_id FROM couples")
    pairs = cursor.fetchall()
    conn.close()
    if pairs:
        q = random.choice(DAILY_QUESTIONS)
        for p in pairs:
            for u_id in [p[0], p[1]]:
                try: await bot.send_message(u_id, f"🔔 **Вечерний вопрос дня для вас:**\n\n{q}", parse_mode="Markdown")
                except Exception: pass

@dp.message(F.text == "📍 Места")
async def cmd_places(message: types.Message):
    user = get_user(message.from_user.id)
    if not user or not user[3]: return
    conn = sqlite3.connect("couple_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT place_name FROM places WHERE user_id = ? OR user_id = ?", (message.from_user.id, user[3]))
    rows = cursor.fetchall()
    conn.close()
    text = "📍 **Куда мы хотим сходить (Список мест):**\n\n"
    if rows:
        for idx, row in enumerate(rows, 1): text += f"{idx}. {row[0]}\n"
    else: text += "Список пуст."
    builder = InlineKeyboardBuilder().button(text="➕ Добавить место", callback_data="add_place")
    await message.answer(text, parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "add_place")
async def callback_add_place(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_place)
    await callback.message.answer("📝 Введите название места или ссылку:")
    await callback.answer()

@dp.message(BotStates.waiting_for_place)
async def save_place(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("couple_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO places (user_id, place_name) VALUES (?, ?)", (message.from_user.id, message.text))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("✅ Место успешно добавлено!")
    user = get_user(message.from_user.id)
    if user and user[3]:
        try: await bot.send_message(user[3], f"📍 Половинка добавила новое место в планы:\n*\"{message.text}\"*", parse_mode="Markdown")
        except Exception: pass

@dp.message(F.text == "⭐ Желания")
async def cmd_wishes(message: types.Message):
    user = get_user(message.from_user.id)
    if not user or not user[3]: return
    conn = sqlite3.connect("couple_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT wish_text FROM wishes WHERE user_id = ? OR user_id = ?", (message.from_user.id, user[3]))
    rows = cursor.fetchall()
    conn.close()
    text = "⭐ **Ваш список общих желаний:**\n\n"
    if rows:
        for idx, row in enumerate(rows, 1): text += f"{idx}. {row[0]}\n"
    else: text += "Список пока пуст."
    builder = InlineKeyboardBuilder().button(text="➕ Добавить желание", callback_data="add_wish")
    await message.answer(text, parse_mode="Markdown", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "add_wish")
async def callback_add_wish(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(BotStates.waiting_for_wish)
    await callback.message.answer("📝 Напишите ваше заветное общее желание:")
    await callback.answer()

@dp.message(BotStates.waiting_for_wish)
async def save_wish(message: types.Message, state: FSMContext):
    conn = sqlite3.connect("couple_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO wishes (user_id, wish_text) VALUES (?, ?)", (message.from_user.id, message.text))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer("✅ Желание сохранено в список!")
    user = get_user(message.from_user.id)
    if user and user[3]:
        try: await bot.send_message(user[3], f"⭐ Половинка добавила желание в список:\n*\"{message.text}\"*", parse_mode="Markdown")
        except Exception: pass

@dp.message(F.text == "⏳ Капсула времени")
async def cmd_capsule(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if not user or not user[3]:
        await message.answer("Сначала настройте пару.")
        return
    await message.answer("⏳ Укажите дату доставки в формате `ДД.ММ.ГГГГ` (например: `14.02.2025`):")
    await state.set_state(BotStates.waiting_for_capsule_date)

@dp.message(BotStates.waiting_for_capsule_date)
async def process_capsule_date(message: types.Message, state: FSMContext):
    try:
        datetime.strptime(message.text, "%d.%m.%Y")
        await state.update_data(c_date=message.text)
        await state.set_state(BotStates.waiting_for_capsule_text)
        await message.answer("📝 Теперь напишите текст секретного письма:")
    except ValueError:
        await message.answer("❌ Неверный формат. Укажите ДД.ММ.ГГГГ:")

@dp.message(BotStates.waiting_for_capsule_text)
async def process_capsule_text(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user = get_user(message.from_user.id)
    if not user or not user[3]: return
    conn = sqlite3.connect("couple_bot.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO time_capsules (sender_id, receiver_id, message_text, deliver_date) VALUES (?, ?, ?, ?)",
                   (message.from_user.id, user[3], message.text, data["c_date"]))
    conn.commit()
    conn.close()
    await state.clear()
    await message.answer(f"🔒 Письмо запечатано до **{data['c_date']}**.", parse_mode="Markdown")

async def check_time_capsules_job():
    today_str = datetime.now().strftime("%d.%m.%Y")
    conn = sqlite3.connect("couple_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, receiver_id, message_text FROM time_capsules WHERE deliver_date = ? AND is_delivered = 0", (today_str,))
    capsules = cursor.fetchall()
    for cap in capsules:
        cap_id, rec_id, text = cap
        try:
            await bot.send_message(rec_id, f"⏳ ✨ **Капсула времени открыта!** ✨\n\n*\"{text}\"*", parse_mode="Markdown")
            cursor.execute("UPDATE time_capsules SET is_delivered = 1 WHERE id = ?", (cap_id,))
        except Exception: pass
    conn.commit()
    conn.close()

@dp.message(F.text == "📊 Статистика")
async def cmd_stats(message: types.Message):
    user = get_user(message.from_user.id)
    if not user or not user[3]: return
    partner = get_user(user[3])
    text = (
        f"📊 **Статистика пары:**\n\n"
        f"👤 Ты: Настроение ({user[4]}), Очки ({user[5]})\n"
        f"👤 Половинка: Настроение ({partner[4]}), Очки ({partner[5]})\n\n"
        f"🏆 **Всего очков:** {user[5] + partner[5]}"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("unlink"))
async def cmd_unlink(message: types.Message):
    user = get_user(message.from_user.id)
    if not user or not user[3]: return
    partner_id = user[3]
    conn = sqlite3.connect("couple_bot.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET partner_id = NULL, points = 0 WHERE user_id IN (?, ?)", (message.from_user.id, partner_id))
    cursor.execute("DELETE FROM couples WHERE user1_id = ? OR user2_id = ?", (message.from_user.id, message.from_user.id))
    conn.commit()
    conn.close()
    await message.answer("💔 Связь разорвана.", reply_markup=types.ReplyKeyboardRemove())
    try: await bot.send_message(partner_id, "💔 Партнёр разорвал связь.", reply_markup=types.ReplyKeyboardRemove())
    except Exception: pass

@dp.message(F.text | F.photo | F.sticker | F.voice | F.video_note | F.video | F.animation)
async def forward_to_partner(message: types.Message):
    user = get_user(message.from_user.id)
    if message.text:
        menu = ["📅 Счётчик дней", "😊 Настроение", "🎲 Задание для двоих", "🧠 Викторина", "❓ Вопрос дня", "⭐ Желания", "📍 Места", "⏳ Капсула времени", "📊 Статистика"]
        if message.text in menu: return
    if user and user[3]:
        try:
            await bot.send_message(user[3], "💌 **Сообщение от половинки:**", parse_mode="Markdown")
            await message.copy_to(chat_id=user[3])
            await message.answer("Преданно доставлено! 🕊️")
        except Exception:
            await message.answer("❌ Не удалось доставить сообщение.")
    else:
        await message.answer("Вы ещё не связаны с партнёром. Используйте /start.")

async def main():
    scheduler.add_job(send_daily_question_job, "cron", hour=21, minute=0)
    scheduler.add_job(check_time_capsules_job, "interval", minutes=1)
    scheduler.start()
    print("Бот успешно запущен со всеми функциями!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
