#!/usr/bin/env python3
import os
import asyncio
import aiohttp
import re

# Берем ключ OmniRoute из переменной окружения
OMNIROUTE_API_KEY = os.getenv("OMNIROUTE_API_KEY", "")

# Адрес вашего OmniRoute с /api/
OMNIROUTE_URL = "https://wb-bot-g44p.onrender.com/api/v1/chat/completions"

# ИСПРАВЛЕНО: Явно указываем провайдера groq, чтобы OmniRoute не путался
MODEL = "groq/openai/gpt-oss-20b"

def build_prompt(product_name: str) -> str:
    return f"""
    Напиши продающее описание для товара на маркетплейсе.
    Товар: {product_name}.
    Описание должно быть привлекательным, коротким (около 3-5 предложений),
    содержать основные преимущества и вызвать желание купить.
    Пиши на русском языке.
    """

async def generate_description(product_name: str) -> str:
    if not OMNIROUTE_API_KEY.strip():
        return "⚠️ У вас не указан API-ключ OmniRoute."

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OMNIROUTE_API_KEY}",
    }

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Ты полезный ассистент, который пишет рекламные тексты."},
            {"role": "user", "content": build_prompt(product_name)},
        ],
        "temperature": 0.7,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OMNIROUTE_URL, headers=headers, json=payload, timeout=90) as resp:
                resp.raise_for_status()
                data = await resp.json()
        choices = data.get("choices", [])
        if choices and "message" in choices[0]:
            return choices[0]["message"]["content"].strip()
        else:
            return "❗️ Неожиданный формат ответа от OmniRoute."
    except Exception as e:
        print(f"ОШИБКА generate_description для {product_name}: {type(e).__name__} - {e}")
        return f"❌ Ошибка: {e}"

async def generate_full_package(product_name: str) -> str:
    if not OMNIROUTE_API_KEY.strip():
        return "⚠️ У вас не указан API-ключ OmniRoute."

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OMNIROUTE_API_KEY}",
    }

    prompt = f"""
    Сгенерируй полный пакет для карточки товара на маркетплейсе.
    Товар: {product_name}.

    Предоставь следующую информацию:
    1. Заголовок (максимум 50 символов) — короткий продающий титул.
    2. Описание (продающее текст, 3-5 предложений, с основными преимуществами).
    3. Ключевые слова (5-7 штук, через запятую).
    4. Хэштеги (3-5 штук, начинающихся с #).

    Верни ответ в формате (каждая часть с новой строки, заголовки в квадратных скобках):

    [HEADER]: <заголовок>
    [DESCRIPTION]: <описание>
    [KEYWORDS]: <ключевое1, ключевое2, ...>
    [HASHTAGS]: <хэштег1, хэштег2, ...>
    """

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "Ты помощник, который генерирует рекламные тексты для товаров."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(OMNIROUTE_URL, headers=headers, json=payload, timeout=90) as resp:
                resp.raise_for_status()
                data = await resp.json()

        choices = data.get("choices", [])
        if not choices or "message" not in choices[0]:
            print(f"ПУСТОЙ ОТВЕТ для {product_name}: {data}")
            return "❗️ Пустой ответ от OmniRoute."

        raw = choices[0]["message"]["content"].strip()
        print(f"ОТВЕТ для {product_name}: {len(raw)} символов, начало: {raw[:100]}")

        header = ""
        description = ""
        keywords = ""
        hashtags = ""
        
        # Надежный парсинг с помощью регулярных выражений
        header_match = re.search(r'\[HEADER\]:\s*(.*)', raw, re.IGNORECASE)
        if header_match:
            header = header_match.group(1).strip()

        description_match = re.search(r'\[DESCRIPTION\]:\s*(.*?)(?=\[|$)', raw, re.IGNORECASE | re.DOTALL)
        if description_match:
            description = description_match.group(1).strip()

        keywords_match = re.search(r'\[KEYWORDS\]:\s*(.*)', raw, re.IGNORECASE)
        if keywords_match:
            keywords = keywords_match.group(1).strip()

        hashtags_match = re.search(r'\[HASHTAGS\]:\s*(.*)', raw, re.IGNORECASE)
        if hashtags_match:
            hashtags = hashtags_match.group(1).strip()

        if not header and not description:
            print(f"ОШИБКА ПАРСИНГА для {product_name}: raw={raw[:200]}")
            return "❗️ Ошибка парсинга ответа."

        header = header[:50]
        result = (
            f"--- Заголовок ({len(header)} символов) ---\n"
            f"{header}\n\n"
            f"--- Описание (продающее) ---\n"
            f"{description}\n\n"
            f"--- Ключевые слова ---\n"
            f"{keywords}\n\n"
            f"--- Хэштеги ---\n"
            f"{hashtags}\n"
        )
        return result
    except Exception as e:
        print(f"ОШИБКА для {product_name}: {type(e).__name__} - {e}")
        return f"❌ Ошибка: {e}"
