import asyncio
import sqlite3
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import google.generativeai as genai

# ПАРАМЕТРЛЕР
TOKEN = "8609450716:AAH-QAyc-p2C57jq65QpdqjBmbpFtkkjzoo"
GEMINI_KEY = "AIzaSyBFAGEpqJarppqmoSSNP_n0OATYqlfrASM"
ADMIN_ID = 7397153270

# AI Баптау
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-pro')

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Мәліметтер базасы
# Файл жолын Render-де сақталу үшін толық көрсеткен дұрыс
db_path = os.path.join(os.getcwd(), 'bullying_bot.db')
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                  (user_id INTEGER PRIMARY KEY, lang TEXT, total_msgs INTEGER DEFAULT 0)''')
conn.commit()

class BotStates(StatesGroup):
    choosing_lang = State()
    chatting = State()

TEXTS = {
    'kz': {
        'welcome': "Сәлем! Бұл анонимді қолдау боты. Сенің есімің ешкімге көрінбейді. Мұнда сен ішіңдегіні айтып, көмек ала аласың.",
        'chat_start': "Сөйлесуді бастайық. Не болғанын айтып берші...",
    },
    'ru': {
        'welcome': "Привет! Это бот анонимной поддержки. Твоё имя никто не узнает. Здесь ты можешь выговориться и получить помощь.",
        'chat_start': "Давай поговорим. Расскажи, что случилось...",
    }
}

@dp.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    # Ескі күйді тазалау (өте маңызды)
    await state.clear()
    
    builder = InlineKeyboardBuilder()
    builder.add(types.InlineKeyboardButton(text="Қазақша 🇰🇿", callback_data="lang_kz"))
    builder.add(types.InlineKeyboardButton(text="Русский 🇷🇺", callback_data="lang_ru"))
    
    await message.answer("Тілді таңдаңыз / Выберите язык:", reply_markup=builder.as_markup())
    await state.set_state(BotStates.choosing_lang)

@dp.callback_query(F.data.startswith("lang_"))
async def set_lang(callback: types.CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    cursor.execute("INSERT OR IGNORE INTO users (user_id, lang) VALUES (?, ?)", (user_id, lang))
    conn.commit()
    
    await state.update_data(lang=lang)
    await callback.message.answer(TEXTS[lang]['welcome'])
    await callback.message.answer(TEXTS[lang]['chat_start'])
    await state.set_state(BotStates.chatting)
    await callback.answer()

@dp.message(BotStates.chatting)
async def ai_chat(message: types.Message, state: FSMContext):
    if message.text == "/admin" or message.text == "/start":
        return # Бұл командалар чатқа кедергі келтірмесін

    data = await state.get_data()
    lang = data.get('lang', 'kz')
    
    cursor.execute("UPDATE users SET total_msgs = total_msgs + 1 WHERE user_id = ?", (message.from_user.id,))
    conn.commit()

    instruction = "Сен мектептегі психологсың. Буллингке ұшыраған балаға анонимді қолдау көрсет. Жылы сөйлес. Жауабың қысқа әрі нұсқа болсын."
    if lang == 'ru':
        instruction = "Ты школьный психолог. Поддержи ребенка, столкнувшегося с буллингом. Отвечай мягко и кратко."

    try:
        # AI-ға сұраныс жіберу
        response = model.generate_content(f"{instruction} \n Пайдаланушы: {message.text}")
        await message.answer(response.text)
    except Exception as e:
        print(f"AI Error: {e}") # Қатені логқа шығару
        await message.answer("Кешіріңіз, қазір байланыс үзілді. Кішкенеден соң қайта жазыңыз.")

@dp.message(F.text == "/admin")
async def admin_stats(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        cursor.execute("SELECT COUNT(*) FROM users")
        count = cursor.fetchone()[0]
        await message.answer(f"📊 Статистика: Ботқа {count} оқушы кірді.")
    else:
        await message.answer("Бұл команда тек админге арналған.")

async def main():
    print("Бот іске қосылды...")
    # drop_pending_updates=True — Conflict қатесін болдырмау үшін өте маңызды
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот тоқтатылды")
