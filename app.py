#!/usr/bin/env python3
import os
import asyncio
import aiohttp
import re

# Ключи из переменных окружения Render
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
ZAI_API_KEY = os.getenv("ZAI_API_KEY", "")

# Настройки провайдеров
PROVIDERS = [
    {
        "name": "Groq",
        "url": "https://api.groq.com/openai/v1/chat/completions",
        "key": GROQ_API_KEY,
        "model": "llama-3.3-70b-versatile",  # Модель с хорошим лимитом
    },
    {
        "name": "Z.ai",
        "url": "https://api.z.ai/api/paas/v4/chat/completions",
        "key": ZAI_API_KEY,
        "model": "glm-4.5-flash",  # Бесплатная модель
    }
]

async def _make_request(provider: dict, prompt: str) -> str:
    """Отправляет запрос к конкретному провайдеру."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {provider['key']}",
    }
    payload = {
        "model": provider["model"],
        "messages": [
            {"role": "system", "content": "Ты помощник, который генерирует рекламные тексты для товаров."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(provider["url"], headers=headers, json=payload, timeout=60) as resp:
            if resp.status == 429:
                raise Exception(f"RATE_LIMIT_{provider['name']}")
            resp.raise_for_status()
            data = await resp.json()
    
    choices = data.get("choices", [])
    if not choices or "message" not in choices[0]:
        raise Exception(f"EMPTY_RESPONSE_{provider['name']}")
    
    return choices[0]["message"]["content"].strip()

async def generate_full_package(product_name: str) -> str:
    # Формируем промпт
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

    last_error = None

    # Пробуем провайдеров по очереди
    for provider in PROVIDERS:
        if not provider["key"].strip():
            continue
        
        try:
            print(f"Попытка использовать {provider['name']}...")
            raw = await _make_request(provider, prompt)
            print(f"УСПЕХ: {provider['name']} ответил.")
            
            # Парсинг ответа
            header = ""
            description = ""
            keywords = ""
            hashtags = ""
            
            header_match = re.search(r'\[HEADER\]:\s*(.*)', raw, re.IGNORECASE)
            if header_match: header = header_match.group(1).strip()

            description_match = re.search(r'\[DESCRIPTION\]:\s*(.*?)(?=\[|$)', raw, re.IGNORECASE | re.DOTALL)
            if description_match: description = description_match.group(1).strip()

            keywords_match = re.search(r'\[KEYWORDS\]:\s*(.*)', raw, re.IGNORECASE)
            if keywords_match: keywords = keywords_match.group(1).strip()

            hashtags_match = re.search(r'\[HASHTAGS\]:\s*(.*)', raw, re.IGNORECASE)
            if hashtags_match: hashtags = hashtags_match.group(1).strip()

            if not header and not description:
                print(f"ОШИБКА ПАРСИНГА ({provider['name']}): raw={raw[:200]}")
                raise Exception("PARSE_ERROR")

            header = header[:50]
            return (
                f"--- Заголовок ({len(header)} символов) ---\n"
                f"{header}\n\n"
                f"--- Описание (продающее) ---\n"
                f"{description}\n\n"
                f"--- Ключевые слова ---\n"
                f"{keywords}\n\n"
                f"--- Хэштеги ---\n"
                f"{hashtags}\n"
            )

        except Exception as e:
            last_error = e
            print(f"ОШИБКА {provider['name']}: {e}. Переключаемся на следующего...")
            continue

    # Если все провайдеры отказали
    return f"❌ Ошибка: все провайдеры недоступны. Последняя ошибка: {last_error}"
