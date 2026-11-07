import asyncio
import json
import os
import csv
from datetime import datetime
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, PreCheckoutQuery, LabeledPrice

from app import generate_full_package

# --- Конфигурация ---
ADMIN_ID = 860288063  # Ваш Telegram ID
PAYMENTS_ENABLED = True

TOKEN = os.environ.get("TELEGRAM_TOKEN")
DATA_FILE = "users.json"
HISTORY_FILE = "history.json"

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()

# --- Работа с файлами данных ---
def load_access():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_access(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

user_access = load_access()
history = load_history()

# --- Парсинг пакета ---
def parse_package(package_text: str):
    sections = {"heading": "", "description": "", "keywords": "", "hashtags": ""}
    current = None
    for line in package_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("--- Заголовок"):
            current = "heading"
            continue
        elif stripped.startswith("--- Описание"):
            current = "description"
            continue
        elif stripped.startswith("--- Ключевые слова"):
            current = "keywords"
            continue
        elif stripped.startswith("--- Хэштеги"):
            current = "hashtags"
            continue
        elif stripped.startswith("---"):
            current = None
            continue
        if current and stripped:
            sections[current] += stripped + " "
    for key in sections:
        sections[key] = sections[key].strip()
    return sections

# --- Создание CSV ---
def create_csv_file(product_name: str, package_text: str, user_id: int) -> str:
    parts = parse_package(package_text)
    csv_path = f"temp_{user_id}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Товар", "Заголовок", "Описание", "Ключевые слова", "Хэштеги"])
        writer.writerow([product_name, parts["heading"], parts["description"], parts["keywords"], parts["hashtags"]])
    return csv_path

# --- Добавление в историю ---
def add_to_history(user_id: int, product_name: str, package_text: str):
    entry = {
        "product": product_name,
        "package": package_text,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    user_key = str(user_id)
    if user_key not in history:
        history[user_key] = []
    history[user_key].append(entry)
    history[user_key] = history[user_key][-10:]
    save_history(history)

def get_user_history(user_id: int, limit: int = 5):
    user_key = str(user_id)
    entries = history.get(user_key, [])
    return entries[-limit:]

# --- Обработчики ---

@router.message(Command("start"))
async def cmd_start(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить 10 генераций за 50 Stars", callback_data="buy")]
    ])
    user_id = str(message.from_user.id)
    balance = user_access.get(user_id, 0)
    await message.answer(
        f"Привет! Я генерирую полный пакет для карточек товаров:\n"
        f"• Заголовок\n"
        f"• Продающее описание\n"
        f"• Ключевые слова\n"
        f"• Хэштеги\n\n"
        f"Отправь мне название товара, и я сделаю всё за 5 секунд!\n\n"
        f"Ваш баланс: {balance} генераций.",
        reply_markup=keyboard
    )

@router.callback_query(lambda c: c.data == "buy")
async def process_buy(callback_query: types.CallbackQuery):
    await bot.send_invoice(
        chat_id=callback_query.message.chat.id,
        title="10 генераций полного пакета",
        description="Пакет из 10 генераций полного пакета для карточек товаров",
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
    user_access[user_id] = user_access.get(user_id, 0) + 10
    save_access(user_access)
    await message.answer("Оплата прошла успешно! Теперь вы можете сгенерировать 10 полных пакетов.")

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id != ADMIN_ID:
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔓 Включить платные функции", callback_data="enable_payments")],
        [InlineKeyboardButton(text="🔒 Выключить платные функции", callback_data="disable_payments")],
        [InlineKeyboardButton(text="🎁 Выдать себе 100 генераций", callback_data="add_generations")]
    ])
    await message.answer("Админ-панель:", reply_markup=keyboard)

@router.message(Command("history"))
async def cmd_history(message: Message):
    entries = get_user_history(message.from_user.id, limit=5)
    if not entries:
        await message.answer("История пуста.")
        return
    text = "Последние генерации:\n"
    for entry in reversed(entries):
        text += f"• {entry['product']} — {entry['date']}\n"
    await message.answer(text)

@router.message()
async def handle_text(message: Message):
    user_id = str(message.from_user.id)

    if PAYMENTS_ENABLED:
        if user_access.get(user_id, 0) <= 0:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Купить 10 генераций за 50 Stars", callback_data="buy")]
            ])
            await message.answer("У вас закончились генерации. Купите еще 10 за 50 Stars.", reply_markup=keyboard)
            return
        user_access[user_id] -= 1
        save_access(user_access)

    product_name = message.text
    description = generate_full_package(product_name)
    add_to_history(message.from_user.id, product_name, description)

    await message.answer(description)

    csv_path = create_csv_file(product_name, description, message.from_user.id)
    await message.answer_document(FSInputFile(csv_path))
    os.remove(csv_path)

    if PAYMENTS_ENABLED:
        await message.answer(f"Хочешь сгенерировать ещё? У тебя осталось {user_access[user_id]} генераций.")
    else:
        await message.answer("Генерация пройдена бесплатно! Хочешь ещё?")

@router.callback_query(lambda c: c.data == "enable_payments")
async def enable_payments(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Только для админа!", show_alert=True)
        return
    global PAYMENTS_ENABLED
    PAYMENTS_ENABLED = True
    await callback.message.answer("Платежи включены.")
    await callback.answer()

@router.callback_query(lambda c: c.data == "disable_payments")
async def disable_payments(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Только для админа!", show_alert=True)
        return
    global PAYMENTS_ENABLED
    PAYMENTS_ENABLED = False
    await callback.message.answer("Платежи выключены. Теперь генерация бесплатна для всех.")
    await callback.answer()

@router.callback_query(lambda c: c.data == "add_generations")
async def add_generations(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Только для админа!", show_alert=True)
        return
    global user_access
    user_id_str = str(callback.from_user.id)
    user_access[user_id_str] = user_access.get(user_id_str, 0) + 100
    save_access(user_access)
    await callback.message.answer("Выдано 100 генераций.")
    await callback.answer()

dp.include_router(router)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
