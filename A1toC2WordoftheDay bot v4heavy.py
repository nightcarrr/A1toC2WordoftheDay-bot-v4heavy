import asyncio
import logging
import random
import nltk
import aiohttp
from nltk.corpus import brown
from aiogram import Bot, Dispatcher, types, Router, F
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

TOKEN = "8093008600:AAExIjF4xUG6kmpOTGlMgNPclovpQTfvtF0"
logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
dp.include_router(router)

nltk.download('brown')
sentences = brown.sents()

def categorize_words():
    """Категоризирует слова по сложности."""
    word_freq = nltk.FreqDist(brown.words())
    easy = {w for w, f in word_freq.items() if f > 200 and len(w) <= 4}
    medium = {w for w, f in word_freq.items() if 50 < f <= 200 and 4 < len(w) <= 7}
    hard = {w for w, f in word_freq.items() if f <= 50 and len(w) > 7}
    return easy, medium, hard

easy_words, medium_words, hard_words = categorize_words()

class QuizState(StatesGroup):
    choosing_level = State()
    waiting_for_answer = State()

def generate_sentence(difficulty):
    """Генерирует предложение с пропущенным словом соответствующей сложности."""
    word_pool = easy_words if difficulty == "Easy" else medium_words if difficulty == "Medium" else hard_words
    while True:
        sentence = random.choice(sentences)
        missing_word = random.choice(sentence)
        if missing_word in word_pool:
            sentence[sentence.index(missing_word)] = '____'
            return " ".join(sentence), missing_word

async def get_definition(word):
    """Получает определение слова из Oxford Dictionary API."""
    url = f"https://od-api.oxforddictionaries.com/api/v2/entries/en/{word.lower()}"
    headers = {"app_id": "YOUR_APP_ID", "app_key": "YOUR_APP_KEY"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                return data["results"][0]["lexicalEntries"][0]["entries"][0]["senses"][0]["definitions"][0]
            return "Определение не найдено."

kb_levels = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Easy")], [KeyboardButton(text="Medium")], [KeyboardButton(text="Hard")]],
    resize_keyboard=True
)

kb_game = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Hint")], [KeyboardButton(text="I give up!")]],
    resize_keyboard=True
)

@router.message(Command("start"))
async def send_welcome(message: types.Message, state: FSMContext):
    await message.answer("Выберите уровень сложности:", reply_markup=kb_levels)
    await state.set_state(QuizState.choosing_level)

@router.message(QuizState.choosing_level, F.text.in_(["Easy", "Medium", "Hard"]))
async def set_difficulty(message: types.Message, state: FSMContext):
    await state.update_data(difficulty=message.text)
    sentence, answer = generate_sentence(message.text)
    await state.update_data(correct_answer=answer)
    await message.answer(f"Заполните пропуск в предложении:\n\n{sentence}", reply_markup=kb_game)
    await state.set_state(QuizState.waiting_for_answer)

@router.message(QuizState.waiting_for_answer, F.text == "Hint")
async def give_hint(message: types.Message, state: FSMContext):
    data = await state.get_data()
    hint = data.get("correct_answer", "")[0:3] + "..."
    await message.answer(f"Подсказка: {hint}")

@router.message(QuizState.waiting_for_answer, F.text == "I give up!")
async def give_up(message: types.Message, state: FSMContext):
    data = await state.get_data()
    correct_answer = data.get("correct_answer")
    await message.answer(f"Правильный ответ: {correct_answer}")
    await send_welcome(message, state)

@router.message(QuizState.waiting_for_answer)
async def check_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    correct_answer = data.get("correct_answer")
    if message.text.strip().lower() == correct_answer.lower():
        definition = await get_definition(correct_answer)
        await message.answer(f"✅ Верно! {correct_answer} — {definition}")
        await send_welcome(message, state)
    else:
        await message.answer("❌ Неверно! Попробуйте еще раз.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
