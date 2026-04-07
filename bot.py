import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import google.generativeai as genai

# ПАРАМЕТРЛЕР (Осында өз деректеріңізді қойыңыз)
TOKEN = "8609450716:AAHI-arhujSAFR9e5kbYUd_2GR-DRWhy15Y"
GEMINI_KEY = "AIzaSyBFAGEpqJarppqmoSSNP_n0OATYqlfrASM" # Google AI Studio-дан тегін аласыз
ADMIN_ID = 7397153270 # Өзіңіздің ID-іңіз (статистика үшін)

# AI Баптау
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-pro')

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Мәліметтер базасы (Статистика үшін)
conn = sqlite3.connect('bullying_bot.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, lang TEXT, total_msgs INTEGER DEFAULT 0)''')
conn.commit()

class BotStates(StatesGroup):
    choosing_lang = State()
    chatting = State()

# Тіл таңдау мәтіндері
TEXTS = {
    'kz': {
        'welcome': "Сәлем! Бұл анонимді қолдау боты. Сенің есімің ешкімге көрінбейді. Мұнда сен ішіңдегіні айтып, көмек ала аласың. Қазір мен саған ЖИ көмегімен жауап беремін.",
        'chat_start': "Сөйлесуді бастайық. Не болғанын айтып берші...",
        'stats': "Статистика: Ботқа {0} оқушы жазды."
    },
    'ru': {
        'welcome': "Привет! Это бот анонимной поддержки. Твоё имя никто не узнает. Здесь ты можешь выговориться и получить помощь. Сейчас я отвечу тебе с помощью ИИ.",
        'chat_start': "Давай поговорим. Расскажи, что случилось...",
        'stats': "Статистика: В бот написали {0} учеников."
    }
}

@dp.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Қазақша 🇰🇿", callback_data="lang_kz"))
    builder.add(types.InlineKeyboardButton(text="Русский 🇷🇺", callback_data="lang_ru"))
    
    await message.answer("Тілді таңдаңыз / Выберите язык:", reply_markup=builder.as_markup())
    await state.set_state(BotStates.choosing_lang)

@dp.callback_query(F.data.startswith("lang_"))
async def set_lang(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    # Базаға жазу
    cursor.execute("INSERT OR IGNORE INTO users (user_id, lang) VALUES (?, ?)", (user_id, lang))
    conn.commit()
    
    await state.update_data(lang=lang)
    await callback.message.answer(TEXTS[lang]['welcome'])
    await callback.message.answer(TEXTS[lang]['chat_start'])
    await state.set_state(BotStates.chatting)
    await callback.answer()

@dp.message(BotStates.chatting)
async def ai_chat(message: types.Message, state: FSMContext):
    data = await state.get_data()
    lang = data.get('lang', 'kz')
    
    # Статистиканы жаңарту
    cursor.execute("UPDATE users SET total_msgs = total_msgs + 1 WHERE user_id = ?", (message.from_user.id,))
    conn.commit()

    # ЖИ-ге нұсқау (Prompt)
    instruction = "Сен мектептегі психологсың. Буллингке ұшыраған балаға анонимді қолдау көрсет. Жылы сөйлес."
    if lang == 'ru':
        instruction = "Ты школьный психолог. Поддержи ребенка, столкнувшегося с буллингом. Отвечай мягко."

    try:
        response = model.generate_content(f"{instruction} \n Баланың сөзі: {message.text}")
        await message.answer(response.text)
    except Exception as e:
        await message.answer("Кешіріңіз, қазір байланыс үзілді. Кішкенеден соң қайта жазыңыз.")

# Админ үшін статистика командасы
@dp.message(F.from_user.id == ADMIN_ID, F.text == "/admin")
async def admin_stats(message: types.Message):
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    await message.answer(f"Жиынтық оқушылар саны: {count}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
