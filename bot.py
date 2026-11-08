import asyncio
import csv
import json
import os
from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
from aiogram import Bot, Dispatcher, Router, types
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, PreCheckoutQuery, LabeledPrice, FSInputFile

from app import generate_full_package

# --- Конфигурация ---
ADMIN_ID = 860288063
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
        json.dump(data, f, ensure_ascii=False, indent=2)

user_access = load_access()

def load_history() -> dict:
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_history(history: dict):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

history = load_history()

def make_progress_bar(current: int, total: int) -> str:
    bar_length = 20
    filled_blocks = round((current / total) * bar_length) if total > 0 else 0
    empty_blocks = bar_length - filled_blocks
    bar = "█" * filled_blocks + "░" * empty_blocks
    return f"{bar} {current} из {total}"

# --- Парсинг пакета ---
def parse_package(package_text: str) -> dict:
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

# --- Создание XLSX (с оформлением) ---
def create_xlsx_file(results: list, user_id: int) -> str:
    wb = Workbook()
    ws = wb.active
    ws.title = "Карточки товаров"

    headers = ["Товар", "Заголовок", "Описание", "Ключевые слова", "Хэштеги"]
    ws.append(headers)

    header_font = Font(name='Arial', size=12, bold=True, color='FFFFFF')
    data_font = Font(name='Arial', size=11, color='000000')
    header_fill = PatternFill(start_color='1F4E78', end_color='1F4E78', fill_type='solid')
    data_fill = PatternFill(start_color='F2F2F2', end_color='F2F2F2', fill_type='solid')
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    for cell in ws[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        cell.border = thin_border

    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 35
    ws.column_dimensions["C"].width = 40
    ws.column_dimensions["D"].width = 25
    ws.column_dimensions["E"].width = 20

    for i, result in enumerate(results, 2):
        ws.cell(row=i, column=1, value=result.get("product", ""))
        ws.cell(row=i, column=2, value=result.get("heading", ""))
        ws.cell(row=i, column=3, value=result.get("description", ""))
        ws.cell(row=i, column=4, value=result.get("keywords", ""))
        ws.cell(row=i, column=5, value=result.get("hashtags", ""))
        for cell in ws[i]:
            cell.font = data_font
            cell.fill = data_fill
            cell.border = thin_border
            cell.alignment = Alignment(vertical='top', wrap_text=True)

    xlsx_path = f"products_{user_id}.xlsx"
    wb.save(xlsx_path)
    return xlsx_path

# --- История ---
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

def get_user_history(user_id: int, limit: int = 5) -> list:
    user_key = str(user_id)
    entries = history.get(user_key, [])
    return entries[-limit:]

# --- Обработчики ---

@router.message(Command("start"))
async def cmd_start(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Купить 10 генераций за 50 Stars", callback_data="buy")],
        [InlineKeyboardButton(text="👀 Пример работы", callback_data="example")],
        [InlineKeyboardButton(text="📁 Загрузить файл", callback_data="upload_file")]
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

@router.callback_query(lambda c: c.data == "example")
async def process_example(callback_query: types.CallbackQuery):
    example_package = (
        "--- Заголовок ---\n"
        "Термокружка с двойной стенкой\n"
        "--- Описание ---\n"
        "Наша термокружка удерживает напитки горячими до 12 часов и холодными до 24 часов. "
        "Эргономичная форма и надежная герметичность сделают ваш день комфортнее.\n"
        "--- Ключевые слова ---\n"
        "термокружка, подарок, доставка, isotherm\n"
        "--- Хэштеги ---\n"
        "#термокружка #подарочно #уют #купить"
    )
    await callback_query.message.answer(
        f"{example_package}\n\n"
        "Вот так выглядит готовый пакет. Хочешь сгенерировать для своего товара? Просто отправь название!"
    )

    parsed = parse_package(example_package)
    example_result = {
        "product": "Термокружка",
        "heading": parsed.get("heading", ""),
        "description": parsed.get("description", ""),
        "keywords": parsed.get("keywords", ""),
        "hashtags": parsed.get("hashtags", "")
    }
    xlsx_path = create_xlsx_file([example_result], callback_query.from_user.id)
    await callback_query.message.answer_document(FSInputFile(xlsx_path))
    os.remove(xlsx_path)

    await callback_query.answer()

@router.callback_query(lambda c: c.data == "upload_file")
async def process_upload_file(callback_query: types.CallbackQuery):
    await callback_query.message.answer(
        "Отправьте мне файл в формате .xlsx или .csv, где в первом столбце перечислены названия товаров. "
        "Я обработаю их и пришлю готовый файл с описаниями. Каждый товар стоит 1 генерацию."
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

# --- Обработчик документов (загрузка файла) ---
@router.message(lambda message: message.document is not None)
async def handle_document(message: Message):
    user_id = str(message.from_user.id)
    document = message.document

    max_file_size = 50 * 1024 * 1024
    if document.file_size > max_file_size:
        await message.answer("Файл слишком большой. Максимальный размер: 50 Мб.")
        return

    file = await bot.get_file(document.file_id)
    file_path = f"temp_{user_id}_{document.file_name}"
    await bot.download_file(file.file_path, file_path)

    file_ext = document.file_name.split(".")[-1].lower() if document.file_name else ""

    products = []
    try:
        if file_ext == "xlsx":
            from openpyxl import load_workbook
            wb = load_workbook(file_path, read_only=False)
            ws = wb.active
            await asyncio.sleep(0.1)
            for row in ws.iter_rows(min_row=2, values_only=True):
                if row[0] is not None:
                    products.append(str(row[0]).strip())
            wb.close()
        elif file_ext == "csv":
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                for row in reader:
                    if row and row[0] is not None:
                        products.append(str(row[0]).strip())
        else:
            await message.answer("Неподдерживаемый формат файла. Используйте .xlsx или .csv.")
            os.remove(file_path)
            return
    except Exception as e:
        await message.answer(f"Ошибка при чтении файла: {str(e)}")
        os.remove(file_path)
        return
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    product_count = len(products)
    if product_count == 0:
        await message.answer("В файле не найдено товаров.")
        return

    current_access = user_access.get(user_id, 0)
    if current_access < product_count:
        needed = product_count - current_access
        await message.answer(
            f"У вас {current_access} генераций, а в файле {product_count} товаров. "
            f"Купите еще {needed}, чтобы обработать весь файл",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Купить 10 генераций за 50 Stars", callback_data="buy")]
            ])
        )
        return

    user_access[user_id] = current_access - product_count
    save_access(user_access)

    status_msg = await message.answer(f"⏳ Обработка файла...\n{make_progress_bar(0, product_count)}\nОсталось: ~{product_count} товаров")

    group_size = 20
    all_results = []
    group_count = 0

    start_time = asyncio.get_event_loop().time()

    for i in range(0, product_count, group_size):
        group_start = asyncio.get_event_loop().time()
        group = products[i:i + group_size]
        group_results = []
        for p in group:
            result = None
            for attempt in range(2):
                try:
                    result = generate_full_package(p)
                    break
                except Exception as e:
                    print(f"Попытка {attempt+1} для {p} не удалась: {e}")
                    await asyncio.sleep(5)

            if result:
                group_results.append(result)
            else:
                group_results.append(Exception("Не удалось после 2 попыток"))

            await asyncio.sleep(3)

        group_end = asyncio.get_event_loop().time()
        group_duration = group_end - group_start
        group_count += 1

        for j, result in enumerate(group_results):
            if isinstance(result, Exception):
                all_results.append({"product": group[j], "heading": "Ошибка генерации", "description": "", "keywords": "", "hashtags": ""})
            elif isinstance(result, str):
                parsed = parse_package(result)
                all_results.append({
                    "product": group[j],
                    "heading": parsed.get("heading", ""),
                    "description": parsed.get("description", ""),
                    "keywords": parsed.get("keywords", ""),
                    "hashtags": parsed.get("hashtags", "")
                })

        processed = min(i + group_size, product_count)
        remaining = product_count - processed

        avg_group_time = (group_end - start_time) / max(group_count, 1)
        estimated_remaining_groups = remaining / group_size
        remaining_time = estimated_remaining_groups * avg_group_time

        time_str = ""
        if remaining_time > 60:
            minutes = int(remaining_time // 60)
            seconds = int(remaining_time % 60)
            time_str = f" (~{minutes} мин {seconds} сек)"
        elif remaining_time > 1:
            time_str = f" (~{int(remaining_time)} сек)"

        await status_msg.edit_text(
            f"⏳ Обработка файла...\n{make_progress_bar(processed, product_count)}\n"
            f"Осталось: ~{remaining} товаров{time_str}"
        )

        if i + group_size < product_count:
            await asyncio.sleep(2)

    xlsx_path = create_xlsx_file(all_results, int(user_id))
    await message.answer_document(FSInputFile(xlsx_path))
    os.remove(xlsx_path)

    await message.answer(f"Генерация завершена! Обработано {len(all_results)} товаров.")

    for result in all_results:
        if result.get("heading") and result.get("heading") != "Ошибка генерации":
            add_to_history(int(user_id), result["product"], f"Head: {result['heading']}")

@router.message()
async def handle_text(message: Message):
    if not message.text:
        return

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
    package = generate_full_package(product_name)
    add_to_history(message.from_user.id, product_name, package)

    await message.answer(package)

    parsed = parse_package(package)
    result = {
        "product": product_name,
        "heading": parsed.get("heading", ""),
        "description": parsed.get("description", ""),
        "keywords": parsed.get("keywords", ""),
        "hashtags": parsed.get("hashtags", "")
    }
    xlsx_path = create_xlsx_file([result], message.from_user.id)
    await message.answer_document(FSInputFile(xlsx_path))
    os.remove(xlsx_path)

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
