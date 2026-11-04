import asyncio
import json
import os
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, PreCheckoutQuery, LabeledPrice

from app import generate_description

TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATA_FILE = "users.json"

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# --- Работа с файлом данных ---
def load_access():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_access(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

user_access = load_access()

# --- Обработчики ---

@router.message(Command("start"))
async def cmd_start(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить 10 генераций за 50 Stars", callback_data="buy")]
    ])
    user_id = str(message.from_user.id)
    balance = user_access.get(user_id, 0)
    
    await message.answer(
        f"Привет! Я генерирую продающие описания для карточек товаров.\n"
        f"Отправь мне название товара, и я напишу текст.\n\n"
        f"Ваш баланс: {balance} генераций.",
        reply_markup=keyboard
    )

@router.callback_query(lambda c: c.data == "buy")
async def process_buy(callback_query: types.CallbackQuery):
    await bot.send_invoice(
        chat_id=callback_query.message.chat.id,
        title="10 генераций описаний",
        description="Пакет из 10 генераций продающих описаний для карточек товаров",
        payload="10_generations_payload",
        currency="XTR",
        prices=[LabeledPrice(label="10 генераций", amount=50)]
    )
    await callback_query.answer()

@router.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@router.message(lambda message: message.successful_payment)
async def process_successful_payment(message: Message):
    user_id = str(message.from_user.id)
    # Начисляем 10 генераций
    user_access[user_id] = user_access.get(user_id, 0) + 10
    save_access(user_access)
    
    await message.answer("Оплата прошла успешно! Теперь вы можете сгенерировать 10 описаний.")

@router.message()
async def handle_text(message: Message):
    user_id = str(message.from_user.id)
    
    if user_access.get(user_id, 0) <= 0:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Купить 10 генераций за 50 Stars", callback_data="buy")]
        ])
        await message.answer("У вас закончились генерации. Купите еще 10 за 50 Stars.", reply_markup=keyboard)
        return

    # Уменьшаем счетчик, сохраняем и генерируем
    user_access[user_id] -= 1
    save_access(user_access)
    
    product_name = message.text
    description = generate_description(product_name)
    
    await message.answer(description)
    await message.answer(f"Хочешь сгенерировать ещё? У тебя осталось {user_access[user_id]} генераций.")

dp.include_router(router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())